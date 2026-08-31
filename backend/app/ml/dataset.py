"""
Synthetic + curated training data for the MailTrace AI intent/phishing classifier.

Categories:
  0 = safe / legitimate
  1 = phishing / credential_harvesting
  2 = bec / executive_impersonation / payment_diversion

This is intentionally small and hand-crafted so the MVP trains instantly
without external datasets. Swap PHISHING_SAMPLES / SAFE_SAMPLES / BEC_SAMPLES
with a real corpus (e.g. Enron + Nazario phishing corpus) for production use.
"""

SAFE_SAMPLES = [
    "Hi team, attached is the agenda for tomorrow's sprint planning meeting.",
    "Please find the quarterly report attached for your review.",
    "Reminder: the office will be closed on Monday for the public holiday.",
    "Thanks for your help yesterday, the deployment went smoothly.",
    "Here are the meeting notes from today's standup call.",
    "Your Amazon order has shipped and will arrive within 3 business days.",
    "Lunch is on me today, let's meet at the usual place at 1pm.",
    "The new office Wi-Fi password is posted on the notice board.",
    "Can you review the pull request I opened this morning when you get a chance?",
    "Happy birthday! Cake is in the break room at 4pm, come celebrate with us.",
    "Attached is the signed NDA for the new vendor contract.",
    "Your monthly newsletter subscription has been renewed successfully.",
    "The conference room booking for 3pm has been confirmed.",
    "Please review the attached invoice for last month's cloud hosting charges.",
    "Reminder: submit your timesheet by end of day Friday.",
    "The library book you reserved is now ready for pickup.",
    "Thank you for attending our webinar, the recording is now available.",
    "Your flight itinerary for next week's conference is attached.",
    "The team lunch has been rescheduled to Thursday at noon.",
    "Please see the updated onboarding checklist for new hires.",
]

PHISHING_SAMPLES = [
    "Your account has been suspended, click here immediately to verify your identity.",
    "Urgent: your password will expire in 24 hours, login now to avoid losing access.",
    "We detected unusual activity on your account, confirm your details now to restore access.",
    "Your mailbox is almost full, click the link below to upgrade your storage immediately.",
    "Security alert: verify your bank account now or it will be permanently locked.",
    "Congratulations, you have won a prize, claim it now by entering your credit card details.",
    "Your Netflix payment failed, update your billing information immediately to avoid suspension.",
    "IT department: your password expires today, click here to reset it now.",
    "Final notice: your PayPal account will be limited unless you verify your information now.",
    "Action required: unusual sign-in attempt detected, confirm your identity within 24 hours.",
    "Your document has been shared with you, click here to view it and sign in to continue.",
    "Dear user, your email storage quota exceeded, upgrade now by verifying your credentials.",
    "We noticed a login from a new device, click here to secure your account immediately.",
    "Your subscription has expired, renew now by entering your payment details on this page.",
    "Tax refund pending: verify your identity here to receive your refund immediately.",
    "Your package could not be delivered, click here to reschedule and confirm your address.",
    "This is your final warning, your account will be deleted unless you verify now.",
    "Click here to reset your Microsoft 365 password before it is locked permanently.",
    "Your invoice payment is overdue, click the link to pay immediately to avoid penalties.",
    "Verify your Apple ID now, unusual activity has been detected on your account.",
]

BEC_SAMPLES = [
    "Hi, I'm in a meeting and can't talk, I need you to process an urgent wire transfer now.",
    "This is the CEO, please purchase gift cards immediately and send me the codes, it's urgent.",
    "I need you to update the bank account details for our vendor payment right away, keep this confidential.",
    "Please process this invoice payment urgently before end of day, don't discuss it with anyone yet.",
    "I'm traveling and unavailable by phone, wire the funds to the new account I'm sending shortly.",
    "As discussed, please change the payroll direct deposit account for me effective immediately.",
    "This is urgent and confidential, I need you to handle a payment for me while I'm out of office.",
    "Kindly update the supplier's bank details as per the attached letter and process payment today.",
    "I need this handled discreetly and quickly, please transfer the funds before the bank closes.",
    "Please respond only to this email, I cannot access my usual account right now, urgent request.",
    "Can you send me the W-2 forms for all employees today, I need them for an urgent audit.",
    "I'm changing my routing number, please update it in payroll immediately and confirm once done.",
    "Time sensitive: please wire $45,000 to the account below before 3pm today, do not delay.",
    "I need you to buy 5 Amazon gift cards worth $200 each and email me the codes right now.",
    "This is a highly confidential acquisition, only communicate through this email until further notice.",
]

LABEL_MAP = {0: "safe", 1: "phishing", 2: "bec"}


def build_dataset():
    texts, labels = [], []
    for t in SAFE_SAMPLES:
        texts.append(t)
        labels.append(0)
    for t in PHISHING_SAMPLES:
        texts.append(t)
        labels.append(1)
    for t in BEC_SAMPLES:
        texts.append(t)
        labels.append(2)
    return texts, labels
