// Mot de passe hashé (à remplacer par votre propre hash)
const ADMIN_PASSWORD_HASH = "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"; // "password" en SHA-256

// Mettre à false pour réactiver la vérification du mot de passe
const DISABLE_PASSWORD_CHECK = true;

// Variables pour la limitation des tentatives
let loginAttempts = 0;
const MAX_LOGIN_ATTEMPTS = 5;
const LOCKOUT_TIME = 30 * 60 * 1000; // 30 minutes

// Fonction pour hacher le mot de passe avec SHA-256
async function hashPassword(password) {
  const encoder = new TextEncoder();
  const data = encoder.encode(password);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  return hashHex;
}

// Gestionnaire pour le bouton d'administration
document.getElementById('adminButton').addEventListener('click', function() {
  // Vérifier si l'utilisateur est verrouillé
  const lockoutTime = localStorage.getItem('loginLockout');
  if (lockoutTime && parseInt(lockoutTime) > Date.now()) {
    const remainingMinutes = Math.ceil((parseInt(lockoutTime) - Date.now()) / 60000);
    alert(`Accès temporairement bloqué. Veuillez réessayer dans ${remainingMinutes} minute(s).`);
    return;
  }
  
  // Vérifier si une session est déjà active
  if (sessionStorage.getItem('adminAuthenticated') === 'true') {
    // Ouvrir directement le modal d'administration
    new bootstrap.Modal(document.getElementById('adminModal')).show();
  } else {
    // Ouvrir le modal d'authentification
    new bootstrap.Modal(document.getElementById('authModal')).show();
  }
});

// Gestionnaire pour le formulaire d'authentification
document.getElementById('authForm').addEventListener('submit', async function(e) {
  e.preventDefault();

  if (DISABLE_PASSWORD_CHECK) {
    // Authentification automatique si la vérification est désactivée
    sessionStorage.setItem('adminAuthenticated', 'true');
    bootstrap.Modal.getInstance(document.getElementById('authModal')).hide();
    new bootstrap.Modal(document.getElementById('adminModal')).show();
    this.reset();
    return;
  }

  // Vérification normale du mot de passe si activée
  const password = document.getElementById('adminPassword').value;
  const passwordHash = await hashPassword(password);

  if (passwordHash === ADMIN_PASSWORD_HASH) {
    loginAttempts = 0; 
    sessionStorage.setItem('adminAuthenticated', 'true');
    bootstrap.Modal.getInstance(document.getElementById('authModal')).hide();
    new bootstrap.Modal(document.getElementById('adminModal')).show();
    this.reset();
    document.getElementById('adminPassword').classList.remove('is-invalid');
  } else {
    loginAttempts++;
    document.getElementById('adminPassword').classList.add('is-invalid');
    
    const attemptsLeft = MAX_LOGIN_ATTEMPTS - loginAttempts;
    if (attemptsLeft > 0) {
      document.querySelector('.invalid-feedback').textContent = 
        `Mot de passe incorrect. ${attemptsLeft} tentative(s) restante(s).`;
    } else {
      document.querySelector('.invalid-feedback').textContent = 
        "Dernière tentative avant verrouillage temporaire.";
    }
  }
});

// Déconnexion à la fermeture du modal d'administration
document.getElementById('adminModal').addEventListener('hidden.bs.modal', function() {
  // Option 1: Déconnexion immédiate (décommentez pour activer)
  // sessionStorage.removeItem('adminAuthenticated');
  
  // Option 2: Session temporaire (15 minutes)
  setTimeout(() => {
    sessionStorage.removeItem('adminAuthenticated');
  }, 15 * 60 * 1000);
});

// Script pour la configuration du mail
document.querySelector('#monFormulaire').addEventListener('submit', function(e) {
    e.preventDefault();

    const formData = new FormData(this);
    const data = Object.fromEntries(formData.entries());

    // Gestion spéciale pour checkbox (on/off)
    data.email_notifications = formData.get('email_notifications') ? 'on' : 'off';

    fetch('/admin/save-config', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        console.log(result);
        // Gérer le résultat ici
    })
    .catch(error => console.error('Erreur:', error));
});

// Gestion de l'interface d'administration
function saveConfig() {
  const tunnelConfig = Object.fromEntries(new FormData(document.getElementById('tunnelConfig')));
  
  fetch('/admin/save-config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(tunnelConfig)
  })
  .then(response => {
    if (response.ok) {
      showToast('Configuration sauvegardée');
      setTimeout(() => location.reload(), 1000);
    } else {
      showToast('Erreur lors de la sauvegarde', 'error');
    }
  })
  .catch(error => {
    console.error('Erreur:', error);
    showToast('Erreur lors de la sauvegarde', 'error');
  });
}

// Actualisation des logs
function refreshLogs() {
  fetch('/admin/logs')
    .then(response => response.text())
    .then(logs => {
      const logsElement = document.getElementById('tunnelLogs');
      logsElement.textContent = logs;
      // Forcer le scroll vers le bas immédiatement après l'actualisation
      requestAnimationFrame(() => {
        logsElement.scrollTop = logsElement.scrollHeight;
      });
    })
    .catch(error => {
      console.error('Erreur:', error);
      document.getElementById('tunnelLogs').textContent = 'Erreur lors du chargement des logs';
    });
}

// Actualisation automatique
let logsInterval;

document.addEventListener('DOMContentLoaded', function() {
  const checkbox = document.getElementById('autoRefreshLogs');
  if (!checkbox) return;
  
  // Récupérer l'état sauvegardé
  const savedState = localStorage.getItem('autoRefreshEnabled');
  
  // Si un état était sauvegardé, l'appliquer
  if (savedState === 'true') {
    checkbox.checked = true;
    logsInterval = setInterval(refreshLogs, 5000);
  }
  // Actualisation initiale
  refreshLogs();
  
  // Gestion de l'auto-actualisation
  checkbox.addEventListener('change', function() {
    if (this.checked) {
      logsInterval = setInterval(refreshLogs, 5000);
      localStorage.setItem('autoRefreshEnabled', 'true');
    } else {
      clearInterval(logsInterval);
      localStorage.setItem('autoRefreshEnabled', 'false');
    }
  });
});

// Fonctions de contrôle du tunnel
function startTunnel() {
  fetch('/admin/start-tunnel', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        showToast('Tunnel démarré avec succès');
        setTimeout(() => location.reload(), 1000);
      } else {
        showToast('Erreur lors du démarrage du tunnel', 'error');
      }
    })
    .catch(error => {
      console.error('Erreur:', error);
      showToast('Erreur lors du démarrage du tunnel', 'error');
    });
}

function stopTunnel() {
  fetch('/admin/stop-tunnel', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        showToast('Tunnel arrêté avec succès');
        setTimeout(() => location.reload(), 1000);
      } else {
        showToast('Erreur lors de l\'arrêt du tunnel', 'error');
      }
    })
    .catch(error => {
      console.error('Erreur:', error);
      showToast('Erreur lors de l\'arrêt du tunnel', 'error');
    });
}

function enableService() {
  fetch('/admin/enable-service', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        showToast('Service activé avec succès');
      } else {
        showToast('Erreur lors de l\'activation du service', 'error');
      }
    })
    .catch(error => {
      console.error('Erreur:', error);
      showToast('Erreur lors de l\'activation du service', 'error');
    });
}

function disableService() {
  fetch('/admin/disable-service', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        showToast('Service désactivé avec succès');
      } else {
        showToast('Erreur lors de la désactivation du service', 'error');
      }
    })
    .catch(error => {
      console.error('Erreur:', error);
      showToast('Erreur lors de la désactivation du service', 'error');
    });
}

function enableCrontab() {
  fetch('/admin/enable-crontab', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        showToast('Crontab activé avec succès');
      } else {
        showToast('Erreur lors de l\'activation du crontab', 'error');
      }
    })
    .catch(error => {
      console.error('Erreur:', error);
      showToast('Erreur lors de l\'activation du crontab', 'error');
    });
}

function disableCrontab() {
  fetch('/admin/disable-crontab', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        showToast('Crontab désactivé avec succès');
      } else {
        showToast('Erreur lors de la désactivation du crontab', 'error');
      }
    })
    .catch(error => {
      console.error('Erreur:', error);
      showToast('Erreur lors de la désactivation du crontab', 'error');
    });
}