/**
 * MailTrace AI — Gmail Add-on
 * Phase 1:
 * Compact contextual UI only.
 *
 * Backend analysis/auth integration will be connected later.
 */

function buildHomepage(e) {
  return buildMailTraceCard_();
}

function buildAddOn(e) {
  return buildMailTraceCard_();
}


/**
 * Main compact MailTrace UI
 */
function buildMailTraceCard_() {

  const header = CardService.newCardHeader()
    .setTitle('MailTrace AI')
    .setSubtitle('Email Security');

  const section = CardService.newCardSection();

  section
    .addWidget(
      CardService.newDecoratedText()
        .setTopLabel('Current Email')
        .setText('MailTrace is ready')
        .setBottomLabel('AI-powered email threat detection')
    )

    .addWidget(
      CardService.newTextParagraph()
        .setText(
          '🛡️ <b>Email security analysis</b><br>' +
          'Open an email to view its MailTrace security status.'
        )
    )

    .addWidget(
      CardService.newDecoratedText()
        .setTopLabel('Risk')
        .setText('—')
        .setBottomLabel('Analysis will appear here')
    )

    .addWidget(
      CardService.newDecoratedText()
        .setTopLabel('Status')
        .setText('Ready')
        .setBottomLabel('MailTrace AI protection')
    );

  return CardService.newCardBuilder()
    .setHeader(header)
    .addSection(section)
    .build();
}