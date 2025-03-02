// Gestion du mode sombre
const darkModeToggle = document.getElementById('darkModeToggle');
const icon = darkModeToggle.querySelector('i');
const htmlElement = document.documentElement;

// Vérifier la préférence système
const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
const currentTheme = localStorage.getItem('theme');

if (currentTheme === 'dark' || (!currentTheme && prefersDarkScheme.matches)) {
  htmlElement.setAttribute('data-bs-theme', 'dark');
  icon.classList.replace('fa-moon', 'fa-sun');
}

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
