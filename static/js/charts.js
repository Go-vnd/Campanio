/**
 * Companio - Chart.js Initializer
 * Renders statistical charts for Admin Analytics, Volunteer Dashboard, and User Reports
 */

document.addEventListener('DOMContentLoaded', () => {
  renderAdminCharts();
  renderVolunteerCharts();
});

function renderAdminCharts() {
  // Monthly Assistance Request Trends Chart (Line Chart)
  const reqChartCtx = document.getElementById('requestsTrendChart')?.getContext('2d');
  if (reqChartCtx) {
    new Chart(reqChartCtx, {
      type: 'line',
      data: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug'],
        datasets: [{
          label: 'Completed Assistance Requests',
          data: [65, 85, 110, 145, 190, 240, 310, 380],
          borderColor: '#1d4ed8',
          backgroundColor: 'rgba(29, 78, 216, 0.1)',
          fill: true,
          tension: 0.4
        }, {
          label: 'New Volunteer Registrations',
          data: [20, 35, 45, 60, 75, 90, 120, 150],
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          fill: true,
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: 'bottom' }
        },
        scales: {
          y: { beginAtZero: true }
        }
      }
    });
  }

  // Category Distribution (Doughnut Chart)
  const categoryChartCtx = document.getElementById('categoryDistributionChart')?.getContext('2d');
  if (categoryChartCtx) {
    new Chart(categoryChartCtx, {
      type: 'doughnut',
      data: {
        labels: ['Mobility Support', 'Sign Language', 'Audio / Visual Reading', 'Tech Assistance', 'Companionship'],
        datasets: [{
          data: [35, 25, 20, 12, 8],
          backgroundColor: ['#1d4ed8', '#0ea5e9', '#10b981', '#f59e0b', '#8b5cf6']
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: 'right' }
        }
      }
    });
  }

  // Volunteer Rating Breakdown (Bar Chart)
  const ratingChartCtx = document.getElementById('volunteerRatingChart')?.getContext('2d');
  if (ratingChartCtx) {
    new Chart(ratingChartCtx, {
      type: 'bar',
      data: {
        labels: ['5 Stars', '4 Stars', '3 Stars', '2 Stars', '1 Star'],
        datasets: [{
          label: 'User Reviews',
          data: [420, 85, 12, 3, 1],
          backgroundColor: '#3b82f6',
          borderRadius: 8
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false }
        }
      }
    });
  }
}

function renderVolunteerCharts() {
  // Hours Volunteered Chart (Volunteer Dashboard)
  const hoursChartCtx = document.getElementById('volunteerHoursChart')?.getContext('2d');
  if (hoursChartCtx) {
    new Chart(hoursChartCtx, {
      type: 'bar',
      data: {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        datasets: [{
          label: 'Hours Given This Week',
          data: [2, 4, 1.5, 3, 5, 6, 2],
          backgroundColor: '#0ea5e9',
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        scales: {
          y: { beginAtZero: true }
        }
      }
    });
  }
}
