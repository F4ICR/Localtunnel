js/utils.js
// Fonctions utilitaires
function copyToClipboard(elementId) {
  const copyText = document.getElementById(elementId);
  copyText.select();
  document.execCommand("copy");
  showTooltip(copyText, 'Copié !');
}

function showTooltip(element, message) {
  const tooltip = new bootstrap.Tooltip(element, {
    title: message,
    trigger: 'manual'
  });
  tooltip.show();
  setTimeout(() => tooltip.hide(), 1000);
}

function decimalToTime(decimal) {
  const hours = Math.floor(decimal);
  const minutes = Math.round((decimal % 1) * 60);
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
}

async function testCurl(tunnelUrl) {
  const response = await fetch('/test_curl', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({url: tunnelUrl})
  });
  const result = await response.text();
  document.getElementById('curlResult').innerHTML = ' → ' + result;
}
