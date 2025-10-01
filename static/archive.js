// API Base URL
const API_BASE = window.location.origin;

// Chart instances
let clvDistributionChart = null;
let matchesTimelineChart = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  loadArchive();
  loadArchiveStats();
});

// Show loading indicator
function showLoading() {
  document.getElementById("loading").style.display = "block";
}

// Hide loading indicator
function hideLoading() {
  document.getElementById("loading").style.display = "none";
}

// Show status message
function showStatus(message, type = "success") {
  const statusEl = document.getElementById("status-message");
  statusEl.textContent = message;
  statusEl.className = `status-message ${type}`;
  statusEl.style.display = "block";

  setTimeout(() => {
    statusEl.style.display = "none";
  }, 5000);
}

// Load archive statistics
async function loadArchiveStats() {
  try {
    const response = await fetch(`${API_BASE}/api/archive/stats`);
    const data = await response.json();

    if (data.status === "success") {
      const stats = data.stats;

      document.getElementById("stat-total-archived").textContent =
        stats.total_archived;
      document.getElementById("stat-with-closing").textContent =
        stats.with_closing_lines;
      document.getElementById(
        "stat-capture-rate"
      ).textContent = `${stats.closing_line_capture_rate.toFixed(0)}%`;
      document.getElementById("stat-with-bets").textContent = stats.with_bets;
    }
  } catch (error) {
    console.error("Failed to load archive stats:", error);
  }
}

// Load archived matches
async function loadArchive() {
  showLoading();

  try {
    const sportFilter = document.getElementById("sport-filter-archive").value;
    const limitFilter = document.getElementById("limit-filter").value;

    let url = `${API_BASE}/api/archive/matches?`;
    if (sportFilter) url += `sport=${sportFilter}&`;
    if (limitFilter) url += `limit=${limitFilter}`;

    const response = await fetch(url);
    const data = await response.json();

    if (data.status === "success") {
      renderArchive(data.matches || []);
      renderCharts(data.matches || []);
    } else {
      showStatus("Failed to load archive", "error");
    }
  } catch (error) {
    console.error("Failed to load archive:", error);
    showStatus("Failed to load archive", "error");
  } finally {
    hideLoading();
  }
}

// Render archive table
function renderArchive(matches) {
  const tbody = document.getElementById("archive-body");

  // Filter out matches that don't have EV data
  const matchesWithEv = matches.filter(
    (match) =>
      match.best_ev_pct !== null &&
      match.best_ev_pct !== undefined &&
      (match.home_ev_pct !== null || match.away_ev_pct !== null)
  );

  if (!matchesWithEv || matchesWithEv.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="10" class="no-data">No archived matches with EV data found</td></tr>';
    return;
  }

  tbody.innerHTML = matchesWithEv
    .map((match) => {
      // Format start time
      let startTime = "Unknown";
      if (match.start_time) {
        try {
          const date = new Date(match.start_time);
          startTime = date.toLocaleString("en-US", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          });
        } catch (e) {
          startTime = "Invalid Date";
        }
      }

      // Sport badge
      const sport = match.sport || "unknown";
      const sportClass = sport === "cs2" ? "sport-cs2" : "sport-lol";
      const sportLabel =
        sport === "cs2" ? "CS2" : sport === "lol" ? "LoL" : sport.toUpperCase();

      // Opening odds
      const openingHome = match.home_fair_odds
        ? match.home_fair_odds.toFixed(2)
        : "-";
      const openingAway = match.away_fair_odds
        ? match.away_fair_odds.toFixed(2)
        : "-";

      // Closing odds
      const closingHome = match.home_closing_odds
        ? match.home_closing_odds.toFixed(2)
        : "-";
      const closingAway = match.away_closing_odds
        ? match.away_closing_odds.toFixed(2)
        : "-";

      // Line movement
      let lineMovement = "-";
      let lineMovementClass = "";
      if (match.home_clv_move !== null || match.away_clv_move !== null) {
        const homMove = match.home_clv_move || 0;
        const awayMove = match.away_clv_move || 0;
        const avgMove = (homMove + awayMove) / 2;
        lineMovement = `${avgMove > 0 ? "+" : ""}${avgMove.toFixed(1)}%`;
        lineMovementClass = avgMove > 0 ? "line-move-up" : "line-move-down";
      }

      // Bets placed
      const betsPlaced = match.bet_count || 0;
      const betsInfo =
        betsPlaced > 0
          ? `${betsPlaced} (${match.bets_won || 0}W-${match.bets_lost || 0}L)`
          : "-";

      // Average CLV
      let avgClv = "-";
      let avgClvClass = "";
      if (match.avg_clv !== null) {
        avgClv = `${match.avg_clv > 0 ? "+" : ""}${match.avg_clv.toFixed(2)}%`;
        avgClvClass = match.avg_clv >= 0 ? "clv-positive" : "clv-negative";
      }

      // Best EV
      let bestEv = "-";
      let bestEvClass = "";
      if (match.best_ev_pct !== null) {
        bestEv = `${
          match.best_ev_pct > 0 ? "+" : ""
        }${match.best_ev_pct.toFixed(2)}%`;
        bestEvClass = match.best_ev_pct > 0 ? "ev-positive" : "ev-negative";
      }

      return `
            <tr>
                <td class="text-small">${startTime}</td>
                <td>
                    <span class="sport-badge ${sportClass}">${sportLabel}</span>
                </td>
                <td class="text-small">${escapeHtml(
                  match.event || "Unknown"
                )}</td>
                <td>
                    <div class="team-matchup-small">
                        ${escapeHtml(match.home_team)} vs ${escapeHtml(
        match.away_team
      )}
                    </div>
                </td>
                <td class="text-small">
                    <div>${openingHome} / ${openingAway}</div>
                </td>
                <td class="text-small">
                    <div>${closingHome} / ${closingAway}</div>
                </td>
                <td>
                    <span class="line-movement ${lineMovementClass}">${lineMovement}</span>
                </td>
                <td class="text-small">${betsInfo}</td>
                <td>
                    <span class="clv-value ${avgClvClass}">${avgClv}</span>
                </td>
                <td>
                    <span class="ev-value ${bestEvClass}">${bestEv}</span>
                </td>
            </tr>
        `;
    })
    .join("");
}

// Render charts
function renderCharts(matches) {
  if (!matches || matches.length === 0) {
    return;
  }

  // Filter out matches without EV data for charts as well
  const matchesWithEv = matches.filter(
    (match) =>
      match.best_ev_pct !== null &&
      match.best_ev_pct !== undefined &&
      (match.home_ev_pct !== null || match.away_ev_pct !== null)
  );

  renderCLVDistribution(matchesWithEv);
  renderMatchesTimeline(matchesWithEv);
}

// Render CLV distribution chart
function renderCLVDistribution(matches) {
  const ctx = document.getElementById("clv-distribution-chart");

  if (!ctx) return;

  // Destroy existing chart
  if (clvDistributionChart) {
    clvDistributionChart.destroy();
  }

  // Filter matches with closing lines
  const matchesWithClosing = matches.filter(
    (m) =>
      m.home_closing_odds !== null &&
      m.away_closing_odds !== null &&
      (m.home_clv_move !== null || m.away_clv_move !== null)
  );

  if (matchesWithClosing.length === 0) {
    clvDistributionChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: ["No data"],
        datasets: [],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          title: {
            display: true,
            text: "No closing line data available yet",
          },
        },
      },
    });
    return;
  }

  // Group by line movement ranges
  const ranges = {
    "<-5%": 0,
    "-5% to -2%": 0,
    "-2% to 0%": 0,
    "0% to +2%": 0,
    "+2% to +5%": 0,
    ">+5%": 0,
  };

  matchesWithClosing.forEach((match) => {
    const avgMove =
      ((match.home_clv_move || 0) + (match.away_clv_move || 0)) / 2;

    if (avgMove < -5) {
      ranges["<-5%"]++;
    } else if (avgMove < -2) {
      ranges["-5% to -2%"]++;
    } else if (avgMove < 0) {
      ranges["-2% to 0%"]++;
    } else if (avgMove < 2) {
      ranges["0% to +2%"]++;
    } else if (avgMove < 5) {
      ranges["+2% to +5%"]++;
    } else {
      ranges[">+5%"]++;
    }
  });

  clvDistributionChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: Object.keys(ranges),
      datasets: [
        {
          label: "Number of Matches",
          data: Object.values(ranges),
          backgroundColor: [
            "rgba(239, 68, 68, 0.7)",
            "rgba(239, 68, 68, 0.5)",
            "rgba(239, 68, 68, 0.3)",
            "rgba(16, 185, 129, 0.3)",
            "rgba(16, 185, 129, 0.5)",
            "rgba(16, 185, 129, 0.7)",
          ],
          borderColor: [
            "rgba(239, 68, 68, 1)",
            "rgba(239, 68, 68, 1)",
            "rgba(239, 68, 68, 1)",
            "rgba(16, 185, 129, 1)",
            "rgba(16, 185, 129, 1)",
            "rgba(16, 185, 129, 1)",
          ],
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: false,
        },
        title: {
          display: false,
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            stepSize: 1,
          },
        },
      },
    },
  });
}

// Render matches timeline chart
function renderMatchesTimeline(matches) {
  const ctx = document.getElementById("matches-timeline-chart");

  if (!ctx) return;

  // Destroy existing chart
  if (matchesTimelineChart) {
    matchesTimelineChart.destroy();
  }

  // Group matches by day
  const matchesByDay = {};

  matches.forEach((match) => {
    if (match.start_time) {
      try {
        const date = new Date(match.start_time);
        const dayKey = date.toISOString().split("T")[0]; // YYYY-MM-DD

        if (!matchesByDay[dayKey]) {
          matchesByDay[dayKey] = {
            total: 0,
            withClosing: 0,
            withBets: 0,
          };
        }

        matchesByDay[dayKey].total++;
        if (match.home_closing_odds && match.away_closing_odds) {
          matchesByDay[dayKey].withClosing++;
        }
        if (match.bet_count > 0) {
          matchesByDay[dayKey].withBets++;
        }
      } catch (e) {
        console.error("Error parsing date:", e);
      }
    }
  });

  // Sort by date and take last 30 days
  const sortedDays = Object.keys(matchesByDay).sort().slice(-30);

  const labels = sortedDays.map((day) => {
    const date = new Date(day);
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  });

  const totalData = sortedDays.map((day) => matchesByDay[day].total);
  const closingData = sortedDays.map((day) => matchesByDay[day].withClosing);
  const betsData = sortedDays.map((day) => matchesByDay[day].withBets);

  matchesTimelineChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Total Matches",
          data: totalData,
          borderColor: "rgba(59, 130, 246, 1)",
          backgroundColor: "rgba(59, 130, 246, 0.1)",
          tension: 0.4,
          fill: false,
        },
        {
          label: "With Closing Lines",
          data: closingData,
          borderColor: "rgba(16, 185, 129, 1)",
          backgroundColor: "rgba(16, 185, 129, 0.1)",
          tension: 0.4,
          fill: false,
        },
        {
          label: "Had Bets",
          data: betsData,
          borderColor: "rgba(168, 85, 247, 1)",
          backgroundColor: "rgba(168, 85, 247, 0.1)",
          tension: 0.4,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      interaction: {
        mode: "index",
        intersect: false,
      },
      plugins: {
        legend: {
          display: true,
          position: "top",
        },
        title: {
          display: false,
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            stepSize: 1,
          },
        },
      },
    },
  });
}

// Clear archive
async function clearArchive() {
  if (
    !confirm(
      "Are you sure you want to clear all archived matches? This cannot be undone."
    )
  ) {
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/api/archive/clear`, {
      method: "DELETE",
    });

    const data = await response.json();

    if (data.status === "success") {
      showStatus(`Cleared ${data.deleted_count} archived matches`, "success");
      loadArchive();
      loadArchiveStats();
    } else {
      showStatus("Failed to clear archive", "error");
    }
  } catch (error) {
    console.error("Failed to clear archive:", error);
    showStatus("Failed to clear archive", "error");
  }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
