// ===========================
// Fonctions utilitaires
// ===========================

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

// ===========================
// Fonctions liées aux tests de connectivité
// ===========================

// Fonction pour tester l'adresse URL via l'IP publique avec 'curl ifconfig.me'
async function testCurl(tunnelUrl) {
  const response = await fetch('/test_curl', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ url: tunnelUrl })
  });
  const result = await response.text();
  document.getElementById('curlResult').innerHTML = ' → ' + result;
}

// Fonction pour les tests de connectivité
function updateTestStatus() {
  fetch('/check_url')
    .then(response => response.json())
    .then(data => {
      if (data.status === 'success') {
        // Mise à jour individuelle de chaque test
        ['requests', 'curl', 'wget'].forEach(test => {
          const card = document.getElementById(`${test}-card`);
          const status = document.getElementById(`${test}-status`);

          // Mise à jour indépendante de chaque test
          if (data.results[test]) {
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

// ===========================
// Fonctions liées aux métriques système
// ===========================

// Fonction pour actualiser les métriques système
function updateSystemMetrics() {
  fetch('/system_metrics')
    .then(response => response.json())
    .then(data => {
      // Mise à jour de l'horloge
      document.getElementById('current-time').innerHTML =
        `<i class="fas fa-clock me-1"></i> ${data.current_time}`;

      // Mise à jour de la température CPU
      document.getElementById('cpu-temperature').textContent = data.cpu_temperature;

      // Mise à jour de la mémoire
      document.getElementById('memory-info').textContent = data.memory_info;

      // Mise à jour de l'uptime serveur avec gestion d'erreur éventuelle
      const uptimeElement = document.getElementById('system-uptime');
      if (data.system_uptime && data.system_uptime !== "Erreur") {
        uptimeElement.textContent = data.system_uptime;
      } else {
        uptimeElement.innerHTML = '<i class="fas fa-exclamation-triangle text-danger"></i> Indisponible';
      }

      // Animation subtile pour indiquer l'actualisation
      const metricsCard = document.getElementById('system-metrics-card');
      metricsCard.classList.add('border-info');
      setTimeout(() => {
        metricsCard.classList.remove('border-info');
      }, 300);
    })
    .catch(error => {
      console.error('Erreur lors de l\'actualisation des métriques:', error);
    });
}
// Actualisation toutes les 60 secondes (1 minute)
setInterval(updateSystemMetrics, 60000);
// Exécuter immédiatement pour la première actualisation
updateSystemMetrics();

// ===========================
// Fonctions liées aux requêtes et latence réseau
// ===========================

// Fonction d'actualisation du compteur de requêtes
async function refreshRequestCount() {
  try {
    const response = await fetch('/requests_data/');
    if (!response.ok) {
      throw new Error(`Erreur HTTP: ${response.status}`);
    }
    const data = await response.json();

    // Récupérer la dernière valeur du compteur
    const latestCount = data.length > 0 ? data[data.length - 1].count : 0;

    // Mettre à jour l'affichage dans l'élément HTML
    document.getElementById('request-count').innerText = latestCount;
  } catch (error) {
    console.error('Erreur lors de la mise à jour du compteur:', error);
  }
}
// Actualiser immédiatement au chargement puis toutes les 5 secondes
refreshRequestCount();
setInterval(refreshRequestCount, 5000);

// Fonction d'actualisation dynamique de la latence
async function updateLatency() {
  try {
    const response = await fetch('/latency_data/');
    if (!response.ok) {
      throw new Error(`Erreur HTTP: ${response.status}`);
    }
    const data = await response.json();

    document.getElementById('latency-value').innerHTML = `
      ${data.value} <i class="fas fa-satellite fa-xs ms-1"></i>
    `;
  } catch (error) {
    console.error('Erreur lors de la mise à jour de la latence:', error);
    document.getElementById('latency-value').innerHTML = `
      Erreur <i class="fas fa-satellite fa-xs ms-1"></i>
    `;
  }
}
// Actualiser immédiatement au chargement puis toutes les minutes (60000 ms)
updateLatency();
setInterval(updateLatency, 60000);

// ===========================
// Fonctions liées au tunnel
// ===========================

// Fonction d'actualisation dynamique de l'uptime du tunnel
async function updateTunnelUptime() {
  try {
    const response = await fetch('/tunnel_uptime/');
    if (!response.ok) {
      throw new Error(`Erreur HTTP: ${response.status}`);
    }
    const data = await response.json();

    document.getElementById('tunnel-uptime').innerText = data.uptime;
  } catch (error) {
    console.error('Erreur lors de la mise à jour de l\'uptime:', error);
    document.getElementById('tunnel-uptime').innerText = 'Erreur';
  }
}
// Actualisation immédiate puis toutes les minutes (60000 ms)
updateTunnelUptime();
setInterval(updateTunnelUptime, 60000);
