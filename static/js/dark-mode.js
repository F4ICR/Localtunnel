// Gestion du mode sombre
document.addEventListener('DOMContentLoaded', function() {
  const darkModeToggle = document.getElementById('darkModeToggle');
  const icon = darkModeToggle.querySelector('i');
  const htmlElement = document.documentElement;

  // Vérifier la préférence système
  const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
  const currentTheme = localStorage.getItem('theme');

  // Fonction pour mettre à jour le thème des graphiques
  function updateChartTheme() {
    if (typeof updateChart === 'function' && chart) {
      updateChart();
    }
  }

  // Appliquer le thème initial
  if (currentTheme === 'dark' || (!currentTheme && prefersDarkScheme.matches)) {
    htmlElement.setAttribute('data-bs-theme', 'dark');
    icon.classList.replace('fa-moon', 'fa-sun');
  }

  // Gestionnaire d'événement pour le bouton de basculement
  darkModeToggle.addEventListener('click', () => {
    if (htmlElement.getAttribute('data-bs-theme') === 'dark') {
      htmlElement.setAttribute('data-bs-theme', 'light');
      localStorage.setItem('theme', 'light');
      icon.classList.replace('fa-sun', 'fa-moon');
    } else {
      htmlElement.setAttribute('data-bs-theme', 'dark');
      localStorage.setItem('theme', 'dark');
      icon.classList.replace('fa-moon', 'fa-sun');
    }
    updateChartTheme();
  });

  // Écouter les changements de préférence système
  prefersDarkScheme.addEventListener('change', (e) => {
    if (!localStorage.getItem('theme')) {
      if (e.matches) {
        htmlElement.setAttribute('data-bs-theme', 'dark');
        icon.classList.replace('fa-moon', 'fa-sun');
      } else {
        htmlElement.setAttribute('data-bs-theme', 'light');
        icon.classList.replace('fa-sun', 'fa-moon');
      }
      updateChartTheme();
    }
  });
});

// Fonction exportée pour permettre aux autres scripts de mettre à jour les graphiques
function isDarkMode() {
  return document.documentElement.getAttribute('data-bs-theme') === 'dark';
}

// Fonction pour obtenir la couleur de texte appropriée selon le thème
function getThemeTextColor() {
  return isDarkMode() ? '#f8f9fa' : '#212529';
}
