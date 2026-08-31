/**
 * MailTrace AI — Gmail Add-on
 * Shows a compact risk/forensics summary for the currently open Gmail message.
 */

const PROP_BACKEND_URL = 'mailtrace_backend_url';
const PROP_FRONTEND_URL = 'mailtrace_frontend_url';
const PROP_ACCESS_TOKEN = 'mailtrace_access_token';

function buildHomepage(e) {
  return buildSettingsCard_('Connect your MailTrace account to see email risk inside Gmail.');
}

function buildSettingsCard_(message) {
  const props = PropertiesService.getUserProperties();
  const savedUrl = props.getProperty(PROP_BACKEND_URL) || '';
  const savedFrontend = props.getProperty(PROP_FRONTEND_URL) || '';
  const savedToken = props.getProperty(PROP_ACCESS_TOKEN) || '';

  const section = CardService.newCardSection()
    .addWidget(CardService.newTextParagraph().setText(message))
    .addWidget(CardService.newTextInput().setFieldName('backendUrl').setTitle('Backend URL')
      .setHint('https://your-backend.onrender.com').setValue(savedUrl))
    .addWidget(CardService.newTextInput().setFieldName('frontendUrl').setTitle('MailTrace website URL')
      .setHint('https://your-frontend.vercel.app').setValue(savedFrontend))
    .addWidget(CardService.newTextInput().setFieldName('accessToken').setTitle('MailTrace access token')
      .setHint('JWT from the MailTrace website').setValue(savedToken ? '••••••••' : ''))
    .addWidget(CardService.newTextButton().setText('Save')
      .setOnClickAction(CardService.newAction().setFunctionName('onSaveSettings_')));

  return CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader().setTitle('MailTrace AI — Settings'))
    .addSection(section).build();
}

function onSaveSettings_(e) {
  const inputs = e.commonEventObject.formInputs || {};
  const value = (name) => inputs[name]?.stringInputs?.value?.[0] || '';
  const backendUrl = value('backendUrl').replace(/\/+$/, '');
  const frontendUrl = value('frontendUrl').replace(/\/+$/, '');
  const accessToken = value('accessToken');
  const props = PropertiesService.getUserProperties();

  if (backendUrl) props.setProperty(PROP_BACKEND_URL, backendUrl);
  if (frontendUrl) props.setProperty(PROP_FRONTEND_URL, frontendUrl);
  if (accessToken && accessToken !== '••••••••') props.setProperty(PROP_ACCESS_TOKEN, accessToken);

  return CardService.newActionResponseBuilder()
    .setNotification(CardService.newNotification().setText('Saved ✓ Open an email to analyze it.'))
    .setNavigation(CardService.newNavigation().updateCard(buildSettingsCard_('Settings saved ✓')))
    .build();
}

function buildAddOn(e) {
  const props = PropertiesService.getUserProperties();
  const backendUrl = props.getProperty(PROP_BACKEND_URL);
  const frontendUrl = props.getProperty(PROP_FRONTEND_URL) || '';
  const accessToken = props.getProperty(PROP_ACCESS_TOKEN);

  if (!backendUrl || !accessToken) {
    return buildSettingsCard_('Set up your MailTrace connection first, then reopen this email.');
  }

  const messageId = e.gmail && e.gmail.messageId;
  if (!messageId) return buildErrorCard_('Gmail did not provide a message ID. Reopen the email.');

  const result = callBackend_(backendUrl, accessToken,
    `/api/v1/addon/lookup?gmail_message_id=${encodeURIComponent(messageId)}`);

  if (result === null) return buildErrorCard_('Could not reach MailTrace. Check Backend URL and token.');
  if (!result.analyzed) return buildNotAnalyzedCard_();
  return buildResultCard_(result, backendUrl, frontendUrl, accessToken);
}

function buildResultCard_(result, backendUrl, frontendUrl, accessToken) {
  const icons = { ALLOW: '🟢', QUARANTINE: '🟡', BLOCK: '🔴' };
  const icon = icons[result.decision] || '⚪';
  const t = result.threats || {};

  const section = CardService.newCardSection()
    .addWidget(CardService.newDecoratedText().setTopLabel('Decision')
      .setText(`${icon} ${result.decision || 'UNKNOWN'}`)
      .setBottomLabel(`Risk score: ${result.final_risk_score ?? '—'} / 100`))
    .addWidget(CardService.newDecoratedText().setTopLabel('Classification')
      .setText(result.classification || 'Unknown')
      .setBottomLabel(`Thread: ${result.thread_count || 1} • Suspicious: ${result.suspicious_count || 0}`))
    .addWidget(CardService.newTextParagraph().setText(
      `🔗 URLs: ${t.url_count || 0}   •   📎 Attachments: ${t.attachment_count || 0}`));

  (result.reasons || []).slice(0, 4).forEach((reason) => {
    section.addWidget(CardService.newTextParagraph().setText(`⚠️ ${String(reason)}`));
  });

  if (result.quarantine_status === 'quarantined') {
    section.addWidget(CardService.newTextParagraph().setText(
      '⚠️ This email is quarantined. You can review it and release it back to Gmail.'
    ));
  }

  const links = [];
  if (frontendUrl) {
    links.push(CardService.newTextButton().setText('View Case')
      .setOpenLink(CardService.newOpenLink().setUrl(`${frontendUrl}/cases/${encodeURIComponent(result.case_id)}`)));
  }

  // The backend accepts ?token= specifically for browser/PDF links.
  const reportUrl = `${backendUrl}/api/v1/cases/${encodeURIComponent(result.case_id)}/report?token=${encodeURIComponent(accessToken)}`;
  links.push(CardService.newTextButton().setText('View PDF Report')
    .setOpenLink(CardService.newOpenLink().setUrl(reportUrl)));

  if (result.quarantine_status === 'quarantined') {
    links.push(CardService.newTextButton().setText('Release to Inbox')
      .setOnClickAction(CardService.newAction().setFunctionName('releaseCase_')
        .setParameters({ caseId: result.case_id })));
  }

  links.forEach((button) => section.addWidget(button));

  return CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader().setTitle('MailTrace AI').setSubtitle('Email security analysis'))
    .addSection(section).build();
}

function releaseCase_(e) {
  const caseId = e.commonEventObject.parameters.caseId;
  const props = PropertiesService.getUserProperties();
  const backendUrl = props.getProperty(PROP_BACKEND_URL);
  const token = props.getProperty(PROP_ACCESS_TOKEN);
  if (!backendUrl || !token || !caseId) return buildErrorCard_('Missing MailTrace connection or case ID.');

  try {
    const response = UrlFetchApp.fetch(`${backendUrl}/api/v1/cases/${encodeURIComponent(caseId)}/release`, {
      method: 'post', headers: { Authorization: `Bearer ${token}` }, muteHttpExceptions: true,
    });
    if (response.getResponseCode() < 200 || response.getResponseCode() >= 300) {
      return buildErrorCard_(`Release failed (${response.getResponseCode()}). Open MailTrace for details.`);
    }
    return CardService.newActionResponseBuilder()
      .setNotification(CardService.newNotification().setText('Released back to Gmail inbox ✓'))
      .setNavigation(CardService.newNavigation().popToRoot())
      .build();
  } catch (err) {
    return buildErrorCard_('Could not release this message. Check your MailTrace connection.');
  }
}

function buildNotAnalyzedCard_() {
  return CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader().setTitle('MailTrace AI').setSubtitle('Not analyzed yet'))
    .addSection(CardService.newCardSection().addWidget(CardService.newTextParagraph().setText(
      "This email hasn't been analyzed yet. Turn on real-time detection or run Gmail Sync from the MailTrace website, then reopen the email."
    ))).build();
}

function buildErrorCard_(message) {
  return CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader().setTitle('MailTrace AI').setSubtitle('Connection issue'))
    .addSection(CardService.newCardSection().addWidget(CardService.newTextParagraph().setText(message)))
    .build();
}

function callBackend_(backendUrl, accessToken, path) {
  try {
    const response = UrlFetchApp.fetch(`${backendUrl}${path}`, {
      method: 'get', headers: { Authorization: `Bearer ${accessToken}` }, muteHttpExceptions: true,
    });
    if (response.getResponseCode() !== 200) return null;
    return JSON.parse(response.getContentText());
  } catch (err) { return null; }
}
