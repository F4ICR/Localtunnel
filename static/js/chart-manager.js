// Gestion du graphique de la page index
let chart = null;
let chartConfig = null;

async function updateChart() {
  const days = document.getElementById('days').value;
  const minHours = document.getElementById('hoursFilter').value;
  
  try {
    const response = await fetch(`/tunnel_data/${days}?min_hours=${minHours}`);
    const data = await response.json();
    
    const filteredData = data.filter(entry => entry.duration >= parseFloat(minHours));
    const labels = filteredData.map(entry => entry.date);
    const durations = filteredData.map(entry => entry.duration);

    const isDarkMode = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    const textColor = isDarkMode ? '#f8f9fa' : '#212529';

    chartConfig = {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Durée des Tunnels',
          data: durations,
          backgroundColor: isDarkMode ? 'rgba(75, 192, 192, 0.3)' : 'rgba(75, 192, 192, 0.2)',
          borderColor: 'rgba(75, 192, 192, 1)',
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              color: textColor,
              callback: value => decimalToTime(value)
            }
          },
          x: {
            ticks: {
              color: textColor
            }
          }
        },
        plugins: {
          legend: {
            labels: {
              color: textColor
            }
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                const dataPoint = filteredData[context.dataIndex];
                return [
                  `Durée : ${decimalToTime(context.raw)}`,
                  `Début : ${dataPoint.start_time}`,
                  `Fin : ${dataPoint.end_time}`,
                  `URL : ${dataPoint.url}`
                ];
              }
            }
          }
        }
      }
    };

    if (chart) {
      chart.destroy();
    }
    
    const ctx = document.getElementById('tunnelChart').getContext('2d');
    chart = new Chart(ctx, chartConfig);

  } catch (error) {
    console.error('Erreur:', error);
    alert('Erreur lors du chargement des données');
  }
}

function updateChartTheme() {
  if (chart) {
    updateChart();
  }
}

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
  updateChart();
  
  document.getElementById('updateButton').addEventListener('click', async function() {
    const button = this;
    const icon = button.querySelector('i');
    
    button.disabled = true;
    icon.classList.add('fa-spin');
    
    try {
      await updateChart();
    } catch (error) {
      console.error('Erreur lors du rafraîchissement:', error);
    } finally {
      setTimeout(() => {
        icon.classList.remove('fa-spin');
        button.disabled = false;
      }, 500);
    }
  });
  
  document.getElementById('days').addEventListener('change', updateChart);
  document.getElementById('hoursFilter').addEventListener('change', updateChart);
});

let requestsChart = null; // Stockage global de l'instance du graphique

// Fonction pour charger et actualiser les données du graphique
async function updateRequestsChart() {
  try {
    const response = await fetch('/requests_data/');
    if (!response.ok) {
      throw new Error(`Erreur HTTP: ${response.status}`);
    }
    const data = await response.json();

    // Regrouper les données par heure
    const groupedData = {};
    data.forEach(item => {
      const hour = new Date(item.timestamp).getHours();
      const timeKey = `${hour}h`;
      groupedData[timeKey] = (groupedData[timeKey] || 0) + 1;
    });

    // Trier les périodes chronologiquement
    const sortedPeriods = Object.keys(groupedData).sort((a, b) => parseInt(a) - parseInt(b));

    const labels = sortedPeriods;
    const counts = sortedPeriods.map(period => groupedData[period]);

    if (requestsChart === null) {
      // Première initialisation du graphique
      const ctx = document.getElementById('requestsChart').getContext('2d');
      requestsChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            label: 'Nombre de requêtes',
            data: counts,
            backgroundColor: 'rgba(75, 192, 192, 0.5)',
            borderColor: 'rgb(75, 192, 192)',
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          scales: {
            x: { title: { display: true, text: 'Période' } },
            y: { beginAtZero: true, title: { display: true, text: 'Nombre de requêtes' } }
          }
        }
      });
    } else {
      // Mise à jour dynamique du graphique existant
      requestsChart.data.labels = labels;
      requestsChart.data.datasets[0].data = counts;
      requestsChart.update();
    }

  } catch (error) {
    console.error('Erreur lors du chargement des données:', error);
    document.getElementById('requestsChart').innerHTML = 'Erreur lors du chargement des données';
  }
}

// Initialiser le graphique lorsqu'on clique sur l'onglet Statistiques
document.addEventListener('DOMContentLoaded', function() {
  const statsTab = document.querySelector('a[href="#stats"]');
  if (statsTab) {
    statsTab.addEventListener('click', function() {
      setTimeout(() => {
        updateRequestsChart(); // Initialisation immédiate
        setInterval(updateRequestsChart, 5000); // Actualisation toutes les 5 secondes
      }, 100);
    });
  }
});
