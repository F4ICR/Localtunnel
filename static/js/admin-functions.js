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

function saveConfig() {
    const form = document.getElementById('tunnelConfig');
    const statusDiv = document.getElementById('statusMessage') || createStatusElement();
    
    statusDiv.textContent = "Enregistrement en cours...";
    statusDiv.className = "status-message status-pending";
    statusDiv.style.display = "block";
    
    fetch('/update-settings', {
        method: 'POST',
        body: new FormData(form)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            statusDiv.textContent = data.message;
            statusDiv.className = "status-message status-success";
            // Faire disparaître après quelques secondes
            setTimeout(() => { statusDiv.style.display = "none"; }, 1000);
        } else {
            statusDiv.textContent = 'Erreur: ' + data.message;
            statusDiv.className = "status-message status-error";
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        statusDiv.textContent = 'Une erreur est survenue lors de la mise à jour des paramètres.';
        statusDiv.className = "status-message status-error";
    });
}

function createStatusElement() {
    const statusDiv = document.createElement('div');
    statusDiv.id = 'statusMessage';
    statusDiv.className = 'status-message';
    // Insérer à un endroit approprié dans votre page
    document.querySelector('form').after(statusDiv);
    return statusDiv;
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

function performAction(action, params = {}) {
    const data = {
        action: action,
        ...params
    };
    
    fetch('/admin/service-action', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(`Action ${action} réussie`);
            if (action === 'start_tunnel' || action === 'stop_tunnel' || action === 'restart_webserver') {
                setTimeout(() => location.reload(), 1000);
            }
        } else {
            alert(`Erreur lors de l'action ${action}: ${data.message || ''}`);
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        alert(`Erreur lors de l'action ${action}`);
    });
}

// Fonctions simplifiées qui utilisent performAction
function startTunnel() {
    performAction('start_tunnel');
}

function stopTunnel() {
    performAction('stop_tunnel');
}

function enableService() {
    performAction('enable_service');
}

function disableService() {
    performAction('disable_service');
}

function restartWebServer() {
    const webPort = document.querySelector('input[name="web_port"]').value;
    
    // Afficher immédiatement un message
    alert("Redémarrage du serveur web en cours...");
    
    fetch('/admin/service-action', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            action: 'restart_webserver',
            port: webPort
        })
    })
    .then(response => {
        // Cette partie peut ne jamais s'exécuter si le serveur redémarre
        alert("Serveur web redémarré avec succès");
    })
    .catch(error => {
        // Cette erreur est attendue car le serveur redémarre
        console.log("Le serveur redémarre, tentative de reconnexion...");
    })
    .finally(() => {
        // Attendre quelques secondes puis tenter de se reconnecter
        setTimeout(() => {
            // Tenter de se reconnecter à la nouvelle URL si le port a changé
            const newUrl = window.location.protocol + '//' + window.location.hostname + ':' + webPort + window.location.pathname;
            
            // Vérifier si le serveur est de nouveau disponible
            checkServerAvailability(newUrl, 10); // Essayer 10 fois
        }, 3000);
    });
}

// Fonction pour vérifier si le serveur est disponible
function checkServerAvailability(url, maxAttempts, currentAttempt = 1) {
    if (currentAttempt > maxAttempts) {
        alert("Impossible de se reconnecter au serveur après plusieurs tentatives.");
        return;
    }
    
    fetch(url, { method: 'HEAD' })
        .then(response => {
            if (response.ok) {
                // Le serveur est disponible, rediriger
                window.location.href = url;
            } else {
                // Réessayer
                setTimeout(() => checkServerAvailability(url, maxAttempts, currentAttempt + 1), 1000);
            }
        })
        .catch(error => {
            // Réessayer
            setTimeout(() => checkServerAvailability(url, maxAttempts, currentAttempt + 1), 1000);
        });
}