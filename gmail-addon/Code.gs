/**
 * MailTrace AI — Gmail Add-on
 * Gmail open-message analysis + MailTrace backend + Web dashboard link
 */

const BACKEND_URL = 'https://mailtrace-ai-backend.onrender.com';

// IMPORTANT:
// Yahan apna actual Vercel frontend URL daalo.
const FRONTEND_URL = 'https://mail-trace-ai.vercel.app/';

const TOKEN_KEY = 'mailtrace_token';


/**
 * Gmail Add-on homepage
 */
function buildHomepage(e) {
  return buildMailTraceCard_();
}


/**
 * Gmail open-email contextual UI
 */
function buildAddOn(e) {

  const messageId = getCurrentMessageId_(e);

  if (!messageId) {
    return buildMailTraceCard_();
  }

  return buildAnalysisCard_(messageId);
}


/**
 * Get current Gmail message ID
 */
function getCurrentMessageId_(e) {

  try {

    if (
      e &&
      e.gmail &&
      e.gmail.messageId
    ) {
      return e.gmail.messageId;
    }

  } catch (err) {

    console.log(
      'Could not get Gmail message ID: ' + err
    );

  }

  return null;
}


/**
 * Main MailTrace homepage card
 */
function buildMailTraceCard_() {

  const header = CardService.newCardHeader()
    .setTitle('MailTrace AI')
    .setSubtitle('Email Security');


  const section =
    CardService.newCardSection();


  section.addWidget(

    CardService.newDecoratedText()
      .setTopLabel('Protection')
      .setText('🛡️ MailTrace AI')
      .setBottomLabel(
        'AI-powered email threat detection'
      )

  );


  section.addWidget(

    CardService.newTextParagraph()
      .setText(
        '<b>MailTrace is ready.</b><br><br>' +
        'Open an email to view its security analysis.'
      )

  );


  return CardService.newCardBuilder()
    .setHeader(header)
    .addSection(section)
    .build();
}


/**
 * Build analysis card for opened Gmail email
 */
function buildAnalysisCard_(messageId) {

  const header =
    CardService.newCardHeader()
      .setTitle('MailTrace AI')
      .setSubtitle('Security Analysis');


  const section =
    CardService.newCardSection();


  section.addWidget(

    CardService.newTextParagraph()
      .setText(
        '🔍 Checking MailTrace analysis...'
      )

  );


  const result =
    lookupMessage_(messageId);


  /**
   * Backend unavailable
   */
  if (!result) {

    section.addWidget(

      CardService.newTextParagraph()
        .setText(
          '⚠️ <b>Unable to connect</b><br><br>' +
          'MailTrace backend could not be reached.'
        )

    );


    return CardService.newCardBuilder()
      .setHeader(header)
      .addSection(section)
      .build();
  }


  /**
   * Email has not been analyzed yet
   */
  if (!result.analyzed) {

    section.addWidget(

      CardService.newDecoratedText()
        .setTopLabel('Status')
        .setText('⏳ Not analyzed')
        .setBottomLabel(
          'MailTrace has not created a case for this email yet.'
        )

    );


    section.addWidget(

      CardService.newTextParagraph()
        .setText(
          '<b>Open the MailTrace web dashboard</b> ' +
          'to analyze this email and create a security case.'
        )

    );


    return CardService.newCardBuilder()
      .setHeader(header)
      .addSection(section)
      .build();
  }


  /**
   * Existing case
   */

  const risk =
    Number(result.final_risk_score || 0);


  let riskLabel =
    '🟢 LOW RISK';


  if (risk >= 80) {

    riskLabel =
      '🚨 HIGH RISK';

  } else if (risk >= 50) {

    riskLabel =
      '⚠️ MEDIUM RISK';

  }


  /**
   * Threat level
   */
  section.addWidget(

    CardService.newDecoratedText()
      .setTopLabel('Threat Level')
      .setText(riskLabel)
      .setBottomLabel(
        'Risk Score: ' + risk + '/100'
      )

  );


  /**
   * Classification
   */
  section.addWidget(

    CardService.newDecoratedText()
      .setTopLabel('Classification')
      .setText(
        result.classification || 'Unknown'
      )
      .setBottomLabel(
        'Decision: ' +
        (result.decision || 'UNKNOWN')
      )

  );


  /**
   * Reasons
   */
  if (
    result.reasons &&
    result.reasons.length > 0
  ) {

    let reasonsText =
      '<b>Why?</b><br>';


    result.reasons.forEach(
      function(reason) {

        reasonsText +=
          '• ' +
          escapeHtml_(String(reason)) +
          '<br>';

      }
    );


    section.addWidget(

      CardService.newTextParagraph()
        .setText(reasonsText)

    );

  }


  /**
   * Threat indicators
   */
  if (result.threats) {

    const threats =
      result.threats;


    section.addWidget(

      CardService.newDecoratedText()
        .setTopLabel('Indicators')
        .setText(

          'URLs: ' +
          (threats.url_count || 0) +

          '  |  Attachments: ' +

          (threats.attachment_count || 0)

        )
        .setBottomLabel(

          threats.has_header_findings

            ? '⚠ Header findings detected'

            : 'Header analysis available'

        )

    );


    /**
     * Geolocation
     */
    if (
      threats.has_geolocation &&
      threats.geolocation
    ) {

      const geo =
        threats.geolocation;


      let geoText =
        '🌍 Location data available';


      if (
        geo.country ||
        geo.city
      ) {

        geoText =
          '🌍 ' +
          (geo.city || '') +
          (
            geo.city &&
            geo.country
              ? ', '
              : ''
          ) +
          (geo.country || '');

      }


      section.addWidget(

        CardService.newDecoratedText()
          .setTopLabel('Geolocation')
          .setText(geoText)
          .setBottomLabel(
            'Email forensic location analysis'
          )

      );

    }

  }


  /**
   * Quarantine status
   */
  if (result.quarantine_status) {

    section.addWidget(

      CardService.newDecoratedText()
        .setTopLabel('Quarantine')
        .setText(
          String(result.quarantine_status)
        )
        .setBottomLabel(
          'MailTrace case: ' +
          String(result.case_id || '—')
        )

    );

  }


  /**
   * Case action buttons
   */
  if (result.case_id) {


    /**
     * View Full Details button
     */
    const detailsUrl =
      FRONTEND_URL +
      '/cases/' +
      encodeURIComponent(
        String(result.case_id)
      );


    const detailsAction =
      CardService.newOpenLink()
        .setUrl(detailsUrl)
        .setOpenAs(
          CardService.newOpenAs().FULL_SIZE
        );


    section.addWidget(

      CardService.newTextButton()
        .setText('📋 View Full Details')
        .setOpenLink(detailsAction)

    );


    /**
     * Blockchain verification
     */
    const blockchainAction =
      CardService.newAction()
        .setFunctionName(
          'verifyBlockchain'
        )
        .setParameters({

          case_id:
            String(result.case_id)

        });


    section.addWidget(

      CardService.newTextButton()
        .setText(
          '🔐 Verify Blockchain Evidence'
        )
        .setOnClickAction(
          blockchainAction
        )

    );

  }


  /**
   * Footer
   */
  section.addWidget(

    CardService.newTextParagraph()
      .setText(
        '<font color="#64748B">' +
        'MailTrace AI • Email Security & Forensics' +
        '</font>'
      )

  );


  return CardService.newCardBuilder()
    .setHeader(header)
    .addSection(section)
    .build();
}


/**
 * Call MailTrace backend
 */
function lookupMessage_(messageId) {

  try {

    const token =
      PropertiesService
        .getUserProperties()
        .getProperty(TOKEN_KEY);


    /**
     * Authentication token missing
     */
    if (!token) {

      console.log(
        'No MailTrace token found.'
      );

      return null;
    }


    const url =
      BACKEND_URL +
      '/api/v1/addon/lookup?gmail_message_id=' +
      encodeURIComponent(messageId);


    const response =
      UrlFetchApp.fetch(

        url,

        {

          method: 'get',

          headers: {

            'Authorization':
              'Bearer ' + token,

            'Accept':
              'application/json'

          },

          muteHttpExceptions: true

        }

      );


    const status =
      response.getResponseCode();


    const body =
      response.getContentText();


    console.log(
      'Lookup status: ' + status
    );


    console.log(
      body
    );


    if (status !== 200) {

      return null;

    }


    return JSON.parse(body);


  } catch (err) {

    console.log(
      'Lookup error: ' + err
    );


    return null;
  }
}


/**
 * Verify blockchain evidence
 */
function verifyBlockchain(e) {

  const caseId =
    e &&
    e.parameters &&
    e.parameters.case_id;


  if (!caseId) {

    return CardService
      .newActionResponseBuilder()
      .setNotification(

        CardService.newNotification()
          .setText(
            'Case ID not available.'
          )

      )
      .build();

  }


  const token =
    PropertiesService
      .getUserProperties()
      .getProperty(TOKEN_KEY);


  if (!token) {

    return CardService
      .newActionResponseBuilder()
      .setNotification(

        CardService.newNotification()
          .setText(
            'MailTrace authentication not configured.'
          )

      )
      .build();

  }


  try {

    const url =
      BACKEND_URL +
      '/api/v1/cases/' +
      encodeURIComponent(caseId) +
      '/blockchain/verify';


    const response =
      UrlFetchApp.fetch(

        url,

        {

          method: 'get',

          headers: {

            'Authorization':
              'Bearer ' + token,

            'Accept':
              'application/json'

          },

          muteHttpExceptions: true

        }

      );


    const status =
      response.getResponseCode();


    if (status !== 200) {

      return CardService
        .newActionResponseBuilder()
        .setNotification(

          CardService.newNotification()
            .setText(
              'Blockchain verification failed.'
            )

        )
        .build();

    }


    return CardService
      .newActionResponseBuilder()
      .setNotification(

        CardService.newNotification()
          .setText(
            '✓ Blockchain evidence verified.'
          )

      )
      .build();


  } catch (err) {

    console.log(
      'Blockchain verification error: ' +
      err
    );


    return CardService
      .newActionResponseBuilder()
      .setNotification(

        CardService.newNotification()
          .setText(
            'Could not verify blockchain evidence.'
          )

      )
      .build();

  }
}


/**
 * Basic HTML escaping
 */
function escapeHtml_(value) {

  return value
    .replace(
      /&/g,
      '&amp;'
    )
    .replace(
      /</g,
      '&lt;'
    )
    .replace(
      />/g,
      '&gt;'
    )
    .replace(
      /"/g,
      '&quot;'
    )
    .replace(
      /'/g,
      '&#039;'
    );

}