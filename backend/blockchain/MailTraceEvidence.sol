// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * MailTrace AI - Evidence Audit Contract
 *
 * Stores cryptographic proofs of email-security analysis.
 *
 * IMPORTANT:
 * Actual email content is NEVER stored on-chain.
 * Only the case ID, evidence hash and audit event are stored.
 */
contract MailTraceEvidence {
    address public owner;

    struct Evidence {
        bytes32 evidenceHash;
        string eventType;
        uint256 timestamp;
        address recorder;
        bool exists;
    }

    mapping(string => Evidence[]) private caseEvidence;

    event EvidenceRecorded(
        string indexed caseId,
        bytes32 indexed evidenceHash,
        string eventType,
        uint256 timestamp,
        address recorder
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorized");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function recordEvidence(
        string calldata caseId,
        bytes32 evidenceHash,
        string calldata eventType
    ) external onlyOwner {
        require(bytes(caseId).length > 0, "Case ID required");
        require(evidenceHash != bytes32(0), "Evidence hash required");
        require(bytes(eventType).length > 0, "Event type required");

        Evidence memory evidence = Evidence({
            evidenceHash: evidenceHash,
            eventType: eventType,
            timestamp: block.timestamp,
            recorder: msg.sender,
            exists: true
        });

        caseEvidence[caseId].push(evidence);

        emit EvidenceRecorded(
            caseId,
            evidenceHash,
            eventType,
            block.timestamp,
            msg.sender
        );
    }

    function getEvidenceCount(
        string calldata caseId
    ) external view returns (uint256) {
        return caseEvidence[caseId].length;
    }

    function getEvidence(
        string calldata caseId,
        uint256 index
    )
        external
        view
        returns (
            bytes32 evidenceHash,
            string memory eventType,
            uint256 timestamp,
            address recorder,
            bool exists
        )
    {
        require(index < caseEvidence[caseId].length, "Evidence not found");

        Evidence memory evidence = caseEvidence[caseId][index];

        return (
            evidence.evidenceHash,
            evidence.eventType,
            evidence.timestamp,
            evidence.recorder,
            evidence.exists
        );
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Invalid owner");
        owner = newOwner;
    }
}