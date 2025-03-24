// Gestion du graphique de la page index
let chart = null;
let chartConfig = null;

async function updateChart() {
  const days = document.getElementById('days').value;
  const minHours = document.getElementById('hoursFilter').value;
  const isCumulative = document.getElementById('cumulativeCheckbox').checked;
  
  try {
    const response = await fetch(`/tunnel_data/${days}?min_hours=${minHours}`);
    const data = await response.json();
    
    const filteredData = data.filter(entry => entry.duration >= parseFloat(minHours));
    
    const isDarkMode = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    const textColor = isDarkMode ? '#f8f9fa' : '#212529';
    
    if (isCumulative) {
      // Mode cumulatif: regrouper les tunnels par date
      const dateGroups = {};
      filteredData.forEach(entry => {
        if (!dateGroups[entry.date]) {
          dateGroups[entry.date] = [];
        }
        dateGroups[entry.date].push(entry);
      });
      
      const labels = Object.keys(dateGroups);
      
      // Créer un dataset pour chaque position dans la pile
      const maxTunnelsPerDay = Math.max(...Object.values(dateGroups).map(tunnels => tunnels.length));
      const datasets = [];
      
      // Palette de couleurs (20 couleurs)
      const colors = [
        'rgba(31, 119, 180, 0.8)', 'rgba(255, 127, 14, 0.8)', 'rgba(44, 160, 44, 0.8)', 
        'rgba(214, 39, 40, 0.8)', 'rgba(148, 103, 189, 0.8)', 'rgba(140, 86, 75, 0.8)', 
        'rgba(227, 119, 194, 0.8)', 'rgba(127, 127, 127, 0.8)', 'rgba(188, 189, 34, 0.8)', 
        'rgba(23, 190, 207, 0.8)', 'rgba(174, 199, 232, 0.8)', 'rgba(255, 187, 120, 0.8)', 
        'rgba(152, 223, 138, 0.8)', 'rgba(255, 152, 150, 0.8)', 'rgba(197, 176, 213, 0.8)', 
        'rgba(196, 156, 148, 0.8)', 'rgba(247, 182, 210, 0.8)', 'rgba(199, 199, 199, 0.8)', 
        'rgba(219, 219, 141, 0.8)', 'rgba(158, 218, 229, 0.8)'
      ];
      
      // Créer un dataset pour chaque position dans la pile
      for (let i = 0; i < maxTunnelsPerDay; i++) {
        datasets.push({
          label: `Tunnel ${i + 1}`,  // Nécessaire pour Chart.js mais ne sera pas affiché
          data: labels.map(date => {
            const tunnels = dateGroups[date];
            return i < tunnels.length ? tunnels[i].duration : 0;
          }),
          backgroundColor: colors[i % colors.length],
          borderColor: 'rgba(0, 0, 0, 0.1)',
          borderWidth: 1,
          stack: 'stack1'
        });
      }
      
      chartConfig = {
        type: 'bar',
        data: {
          labels: labels,
          datasets: datasets
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              stacked: true,
              ticks: {
                color: textColor,
                callback: value => decimalToTime(value)
              },
              title: {
                display: true,
                text: 'Durée totale (heures)',
                color: textColor
              }
            },
            x: {
              stacked: true,
              ticks: {
                color: textColor
              }
            }
          },
          plugins: {
            legend: {
              display: false  // Désactiver l'affichage des légendes
            },
            tooltip: {
              callbacks: {
                label: function(context) {
                  const tunnelIndex = context.datasetIndex;
                  const date = context.label;
                  const tunnels = dateGroups[date];
                  
                  if (tunnelIndex < tunnels.length && context.raw > 0) {
                    const tunnel = tunnels[tunnelIndex];
                    return [
                      `Tunnel ${tunnelIndex + 1}: ${decimalToTime(tunnel.duration)}`,
                      `Début: ${tunnel.start_time}`,
                      `Fin: ${tunnel.end_time}`,
                      `URL: ${tunnel.url}`
                    ];
                  }
                  return '';
                }
              }
            }
          }
        }
      };
    } else {
      // Mode normal: afficher la durée totale par jour
      const labels = filteredData.map(entry => entry.date);
      const durations = filteredData.map(entry => entry.duration);
      
      chartConfig = {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            label: 'Durée des Tunnels',
            data: durations,
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
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
    }

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
  document.getElementById('cumulativeCheckbox').addEventListener('change', updateChart);
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
