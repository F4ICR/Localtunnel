// Fonctions utilitaires

// Fonction qui permet de copier le contenu d’un élément HTML
function copyToClipboard(elementId) {
  const copyText = document.getElementById(elementId);
  copyText.select();
  document.execCommand("copy");
  showTooltip(copyText, 'Copié !');
}

// Fonction qui affiche temporairement un message tooltip
function showTooltip(element, message) {
  const tooltip = new bootstrap.Tooltip(element, {
    title: message,
    trigger: 'manual'
  });
  tooltip.show();
  setTimeout(() => tooltip.hide(), 1000);
}

// Fonction pour convertir un nombre décimal représentant des heures en format horaire “HH:MM”
function decimalToTime(decimal) {
  const hours = Math.floor(decimal);
  const minutes = Math.round((decimal % 1) * 60);
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
}

// Fonction pour tester l'adresse url via l'ip public avec 'curl ifconfig.me'
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

// Fonction pour les tests de connectivités
function updateTestStatus() {
    fetch('/check_url')
        .then(response => response.json())
        .then(data => {
            if(data.status === 'success') {
                // Mise à jour individuelle de chaque test
                ['requests', 'curl', 'wget'].forEach(test => {
                    const card = document.getElementById(`${test}-card`);
                    const status = document.getElementById(`${test}-status`);
                    
                    // Mise à jour indépendante de chaque test
                    if(data.results[test]) {
                        card.className = 'h-100 p-3 bg-light rounded-3 border border-success';
                        status.innerHTML = '<span class="text-success"><i class="fas fa-check-circle me-1"></i>Connecté</span>';
                    } else {
                        card.className = 'h-100 p-3 bg-light rounded-3 border border-danger';
                        status.innerHTML = '<span class="text-danger"><i class="fas fa-times-circle me-1"></i>Échec</span>';
                    }
                });
            }
        });
}
// Actualisation toutes les 10 secondes
setInterval(updateTestStatus, 10000);
