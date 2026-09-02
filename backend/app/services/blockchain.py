"""
MailTrace AI blockchain evidence service.

The blockchain stores ONLY:
    - case ID
    - SHA-256 evidence hash
    - audit event type

Email content, attachments and personal data stay off-chain.
"""

import logging
from typing import Optional

from web3 import Web3

from app.config import settings

logger = logging.getLogger("mailtrace.blockchain")


CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "caseId", "type": "string"},
            {"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"},
            {"internalType": "string", "name": "eventType", "type": "string"},
        ],
        "name": "recordEvidence",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "string", "name": "caseId", "type": "string"}],
        "name": "getEvidenceCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "string", "name": "caseId", "type": "string"},
            {"internalType": "uint256", "name": "index", "type": "uint256"},
        ],
        "name": "getEvidence",
        "outputs": [
            {"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"},
            {"internalType": "string", "name": "eventType", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "address", "name": "recorder", "type": "address"},
            {"internalType": "bool", "name": "exists", "type": "bool"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


class BlockchainService:
    def __init__(self):
        self.enabled = bool(
            settings.BLOCKCHAIN_ENABLED
            and settings.BLOCKCHAIN_RPC_URL
            and settings.BLOCKCHAIN_CONTRACT_ADDRESS
            and settings.BLOCKCHAIN_PRIVATE_KEY
        )

        self.w3: Optional[Web3] = None
        self.contract = None
        self.account = None

        if not self.enabled:
            return

        try:
            self.w3 = Web3(
                Web3.HTTPProvider(
                    settings.BLOCKCHAIN_RPC_URL,
                    request_kwargs={"timeout": 15},
                )
            )

            if not self.w3.is_connected():
                logger.warning("Blockchain RPC is not reachable")
                self.enabled = False
                return

            self.account = self.w3.eth.account.from_key(
                settings.BLOCKCHAIN_PRIVATE_KEY
            )

            checksum_address = self.w3.to_checksum_address(
                settings.BLOCKCHAIN_CONTRACT_ADDRESS
            )

            self.contract = self.w3.eth.contract(
                address=checksum_address,
                abi=CONTRACT_ABI,
            )

        except Exception as exc:
            logger.exception("Blockchain initialization failed: %s", exc)
            self.enabled = False

    def record_evidence(
        self,
        case_id: str,
        evidence_hash: str,
        event_type: str = "THREAT_ANALYZED",
    ) -> dict:
        """
        Record a MailTrace evidence event on-chain.

        Fail-safe:
        Blockchain failure must NEVER break email analysis.
        """

        if not self.enabled:
            return {
                "status": "disabled",
                "transaction_hash": None,
                "block_number": None,
            }

        try:
            clean_hash = evidence_hash.replace("0x", "").strip()

            if len(clean_hash) != 64:
                raise ValueError(
                    "Evidence hash must be a 64-character SHA-256 hex string"
                )

            evidence_bytes32 = bytes.fromhex(clean_hash)

            nonce = self.w3.eth.get_transaction_count(
                self.account.address,
                "pending",
            )

            chain_id = self.w3.eth.chain_id

            transaction = self.contract.functions.recordEvidence(
                case_id,
                evidence_bytes32,
                event_type,
            ).build_transaction(
                {
                    "from": self.account.address,
                    "nonce": nonce,
                    "chainId": chain_id,
                    "gas": 250000,
                    "gasPrice": self.w3.eth.gas_price,
                }
            )

            signed = self.w3.eth.account.sign_transaction(
                transaction,
                private_key=settings.BLOCKCHAIN_PRIVATE_KEY,
            )

            tx_hash = self.w3.eth.send_raw_transaction(
                signed.raw_transaction
            )

            receipt = self.w3.eth.wait_for_transaction_receipt(
                tx_hash,
                timeout=60,
            )

            return {
                "status": "recorded",
                "transaction_hash": tx_hash.hex(),
                "block_number": receipt.blockNumber,
            }

        except Exception as exc:
            logger.exception(
                "Could not record blockchain evidence for %s: %s",
                case_id,
                exc,
            )

            return {
                "status": "failed",
                "transaction_hash": None,
                "block_number": None,
                "error": str(exc),
            }

    def verify_evidence(
        self,
        case_id: str,
        evidence_hash: str,
    ) -> dict:
        """Verify whether an evidence hash exists on-chain."""

        if not self.enabled:
            return {
                "status": "disabled",
                "verified": False,
            }

        try:
            count = self.contract.functions.getEvidenceCount(
                case_id
            ).call()

            target = evidence_hash.replace("0x", "").strip().lower()

            for index in range(count):
                record = self.contract.functions.getEvidence(
                    case_id,
                    index,
                ).call()

                chain_hash = record[0].hex().lower()

                if chain_hash == target:
                    return {
                        "status": "verified",
                        "verified": True,
                        "case_id": case_id,
                        "evidence_hash": evidence_hash,
                        "event_type": record[1],
                        "timestamp": record[2],
                        "recorder": record[3],
                    }

            return {
                "status": "not_found",
                "verified": False,
                "case_id": case_id,
                "evidence_hash": evidence_hash,
            }

        except Exception as exc:
            logger.exception(
                "Blockchain verification failed for %s: %s",
                case_id,
                exc,
            )

            return {
                "status": "failed",
                "verified": False,
                "error": str(exc),
            }


blockchain_service = BlockchainService()