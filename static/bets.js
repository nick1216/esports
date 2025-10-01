// API Base URL
const API_BASE = window.location.origin;

// Chart instances
let evChart = null;
let profitChart = null;
let evDollarsChart = null;
let evAvChart = null;
let clvChart = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  loadBets();
  loadBetStats();

  // Auto-refresh every 60 seconds
  setInterval(() => {
    loadBets();
    loadBetStats();
  }, 60000);
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

// Load bet statistics
async function loadBetStats() {
  try {
    const response = await fetch(`${API_BASE}/api/bets/stats/summary`);
    const data = await response.json();

    if (data.status === "success") {
      const stats = data.stats;

      document.getElementById("stat-total-bets").textContent = stats.total_bets;
      document.getElementById(
        "stat-total-staked"
      ).textContent = `$${stats.total_staked.toFixed(2)}`;

      const profitEl = document.getElementById("stat-total-profit");
      profitEl.textContent = `$${stats.total_profit.toFixed(2)}`;
      profitEl.style.color = stats.total_profit >= 0 ? "#10b981" : "#ef4444";

      document.getElementById(
        "stat-avg-ev"
      ).textContent = `${stats.avg_ev.toFixed(2)}%`;

      // Total EV in dollars
      const totalEvEl = document.getElementById("stat-total-ev");
      const totalEv = stats.total_ev || 0;
      totalEvEl.textContent = `${totalEv >= 0 ? "+" : ""}$${Math.abs(
        totalEv
      ).toFixed(2)}`;
      totalEvEl.style.color = totalEv >= 0 ? "#10b981" : "#ef4444";

      // CLV stats
      const clvEl = document.getElementById("stat-avg-clv");
      const clvValue = stats.avg_clv || 0;
      clvEl.textContent = `${clvValue > 0 ? "+" : ""}${clvValue.toFixed(2)}%`;
      clvEl.style.color = clvValue >= 0 ? "#10b981" : "#ef4444";

      document.getElementById("stat-positive-clv-rate").textContent = `${(
        stats.positive_clv_rate || 0
      ).toFixed(0)}%`;
    }
  } catch (error) {
    console.error("Failed to load bet stats:", error);
  }
}

// Load bets
async function loadBets() {
  showLoading();

  try {
    const response = await fetch(`${API_BASE}/api/bets`);
    const data = await response.json();

    if (data.status === "success") {
      let bets = data.bets || [];

      // Apply filters
      const statusFilter = document.getElementById("status-filter").value;
      const sportFilter = document.getElementById("sport-filter-bets").value;

      if (statusFilter) {
        bets = bets.filter((bet) => bet.status === statusFilter);
      }

      if (sportFilter) {
        bets = bets.filter((bet) => bet.sport === sportFilter);
      }

      renderBets(bets);
      renderCharts(data.bets || []); // Use all bets for charts
      loadBetStats();
    } else {
      showStatus("Failed to load bets", "error");
    }
  } catch (error) {
    console.error("Failed to load bets:", error);
    showStatus("Failed to load bets", "error");
  } finally {
    hideLoading();
  }
}

// Render bets table
function renderBets(bets) {
  const tbody = document.getElementById("bets-body");

  if (!bets || bets.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="17" class="no-data">No bets found</td></tr>';
    return;
  }

  tbody.innerHTML = bets
    .map((bet) => {
      // Format date
      let placedDate = "Unknown";
      if (bet.placed_at) {
        try {
          const date = new Date(bet.placed_at);
          placedDate = date.toLocaleString("en-US", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          });
        } catch (e) {
          placedDate = "Invalid Date";
        }
      }

      // Sport badge
      const sport = bet.sport || "unknown";
      const sportClass = sport === "cs2" ? "sport-cs2" : "sport-lol";
      const sportLabel =
        sport === "cs2" ? "CS2" : sport === "lol" ? "LoL" : sport.toUpperCase();

      // Status badge
      let statusClass = "status-pending";
      let statusLabel = "Pending";
      if (bet.status === "won") {
        statusClass = "status-won";
        statusLabel = "Won";
      } else if (bet.status === "lost") {
        statusClass = "status-lost";
        statusLabel = "Lost";
      } else if (bet.status === "void") {
        statusClass = "status-void";
        statusLabel = "Void";
      }

      // Calculate profit/loss
      let profitLoss = "-";
      let profitClass = "";
      if (bet.status === "won" && bet.actual_return) {
        const profit = bet.actual_return - bet.stake;
        profitLoss = `+$${profit.toFixed(2)}`;
        profitClass = "profit-positive";
      } else if (bet.status === "lost") {
        profitLoss = `-$${bet.stake.toFixed(2)}`;
        profitClass = "profit-negative";
      } else if (bet.status === "void") {
        profitLoss = "$0.00";
        profitClass = "profit-neutral";
      }

      // EV class
      const evClass = bet.ev_percentage > 0 ? "ev-positive" : "ev-negative";

      // CLV display
      let clvDisplay = "-";
      let clvClass = "";
      if (bet.clv !== null && bet.clv !== undefined) {
        const clvValue = bet.clv;
        clvDisplay = `${clvValue > 0 ? "+" : ""}${clvValue.toFixed(2)}%`;
        clvClass = clvValue >= 0 ? "clv-positive" : "clv-negative";
      } else if (bet.closing_odds) {
        clvDisplay = "Pending";
        clvClass = "clv-pending";
      }

      // Closing odds display
      const closingOddsDisplay = bet.closing_odds
        ? bet.closing_odds.toFixed(2)
        : "-";

      // EV dollar amount
      const evDollars = bet.expected_value || 0;
      const evDollarsClass = evDollars >= 0 ? "ev-positive" : "ev-negative";
      const evDollarsDisplay = `${evDollars >= 0 ? "+" : ""}$${Math.abs(
        evDollars
      ).toFixed(2)}`;

      // Actions dropdown - show for all bets, with current status selected
      let currentStatus = "";
      if (bet.status === "won") currentStatus = "win";
      else if (bet.status === "lost") currentStatus = "loss";
      else if (bet.status === "void") currentStatus = "void";

      const actionsContent = `
        <select class="bet-result-dropdown" onchange="updateBetResult(${
          bet.id
        }, this.value)" data-bet-id="${bet.id}">
          <option value="" ${
            bet.status === "pending" ? "selected" : ""
          }>Pending</option>
          <option value="win" ${
            currentStatus === "win" ? "selected" : ""
          }>Win</option>
          <option value="loss" ${
            currentStatus === "loss" ? "selected" : ""
          }>Loss</option>
          <option value="void" ${
            currentStatus === "void" ? "selected" : ""
          }>Void</option>
        </select>
      `;

      return `
            <tr>
                <td>${bet.id}</td>
                <td>${placedDate}</td>
                <td>
                    <span class="sport-badge ${sportClass}">${sportLabel}</span>
                </td>
                <td class="text-small">${escapeHtml(
                  bet.event || "Unknown"
                )}</td>
                <td>
                    <div class="team-matchup-small">
                        ${escapeHtml(bet.home_team)} vs ${escapeHtml(
        bet.away_team
      )}
                    </div>
                </td>
                <td>
                    <span class="bet-team">${escapeHtml(bet.bet_team)}</span>
                </td>
                <td>${bet.odds.toFixed(2)}</td>
                <td>${closingOddsDisplay}</td>
                <td>$${bet.stake.toFixed(2)}</td>
                <td>
                    <span class="ev-value ${evClass}">${
        bet.ev_percentage > 0 ? "+" : ""
      }${bet.ev_percentage.toFixed(2)}%</span>
                </td>
                <td>
                    <span class="ev-value ${evDollarsClass}">${evDollarsDisplay}</span>
                </td>
                <td>
                    <span class="clv-value ${clvClass}">${clvDisplay}</span>
                </td>
                <td>$${bet.potential_return.toFixed(2)}</td>
                <td>
                    <span class="status-badge ${statusClass}">${statusLabel}</span>
                </td>
                <td>
                    <span class="profit-value ${profitClass}">${profitLoss}</span>
                </td>
                <td>${actionsContent}</td>
                <td class="text-small">${escapeHtml(bet.notes || "-")}</td>
            </tr>
        `;
    })
    .join("");
}

// Update bet result
async function updateBetResult(betId, result) {
  // If selecting "Pending" (empty value), we need to revert the bet to pending status
  if (result === "") {
    // For now, we'll just skip - you could add logic to revert to pending if needed
    showStatus("Cannot revert to pending status", "error");
    loadBets(); // Reload to reset dropdown
    return;
  }

  try {
    // Get bet details to calculate actual return
    const betResponse = await fetch(`${API_BASE}/api/bets/${betId}`);
    const betData = await betResponse.json();

    if (betData.status !== "success") {
      showStatus("Failed to get bet details", "error");
      return;
    }

    const bet = betData.bet;
    let actualReturn = 0;

    if (result === "win") {
      actualReturn = bet.potential_return;
    } else if (result === "loss") {
      actualReturn = 0;
    } else if (result === "void") {
      actualReturn = bet.stake;
    }

    // Update bet result
    const response = await fetch(`${API_BASE}/api/bets/${betId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        result: result,
        actual_return: actualReturn,
      }),
    });

    const data = await response.json();

    if (data.status === "success") {
      showStatus(`Bet updated: ${result}`, "success");
      loadBets(); // Reload to show updated data
    } else {
      showStatus("Failed to update bet", "error");
    }
  } catch (error) {
    console.error("Failed to update bet:", error);
    showStatus("Failed to update bet", "error");
  }
}

// Render charts
function renderCharts(bets) {
  if (!bets || bets.length === 0) {
    return;
  }

  renderEVChart(bets);
  renderProfitChart(bets);
  renderEvDollarsChart(bets);
  renderEvAvChart(bets);
  renderClvChart(bets);
}

// Render EV distribution chart
function renderEVChart(bets) {
  const ctx = document.getElementById("ev-chart");

  if (!ctx) return;

  // Destroy existing chart
  if (evChart) {
    evChart.destroy();
  }

  // Group bets by EV ranges
  const evRanges = {
    "<0%": 0,
    "0-2%": 0,
    "2-5%": 0,
    "5-10%": 0,
    ">10%": 0,
  };

  bets.forEach((bet) => {
    const ev = bet.ev_percentage;
    if (ev < 0) {
      evRanges["<0%"]++;
    } else if (ev < 2) {
      evRanges["0-2%"]++;
    } else if (ev < 5) {
      evRanges["2-5%"]++;
    } else if (ev < 10) {
      evRanges["5-10%"]++;
    } else {
      evRanges[">10%"]++;
    }
  });

  evChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: Object.keys(evRanges),
      datasets: [
        {
          label: "Number of Bets",
          data: Object.values(evRanges),
          backgroundColor: [
            "rgba(239, 68, 68, 0.6)",
            "rgba(59, 130, 246, 0.6)",
            "rgba(16, 185, 129, 0.6)",
            "rgba(34, 197, 94, 0.6)",
            "rgba(168, 85, 247, 0.6)",
          ],
          borderColor: [
            "rgba(239, 68, 68, 1)",
            "rgba(59, 130, 246, 1)",
            "rgba(16, 185, 129, 1)",
            "rgba(34, 197, 94, 1)",
            "rgba(168, 85, 247, 1)",
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

// Render cumulative profit/loss chart
function renderProfitChart(bets) {
  const ctx = document.getElementById("profit-chart");

  if (!ctx) return;

  // Destroy existing chart
  if (profitChart) {
    profitChart.destroy();
  }

  // Sort bets by date
  const sortedBets = [...bets].sort(
    (a, b) => new Date(a.placed_at) - new Date(b.placed_at)
  );

  // Calculate cumulative profit/loss
  let cumulative = 0;
  const cumulativeData = [];
  const labels = [];

  sortedBets.forEach((bet, index) => {
    if (bet.status === "won" && bet.actual_return) {
      cumulative += bet.actual_return - bet.stake;
    } else if (bet.status === "lost") {
      cumulative -= bet.stake;
    }
    // void bets don't change cumulative

    cumulativeData.push(cumulative);
    labels.push(`Bet ${index + 1}`);
  });

  profitChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Cumulative Profit/Loss",
          data: cumulativeData,
          borderColor: "rgba(59, 130, 246, 1)",
          backgroundColor: "rgba(59, 130, 246, 0.1)",
          tension: 0.4,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: true,
        },
        title: {
          display: false,
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: function (value) {
              return "$" + value.toFixed(2);
            },
          },
        },
      },
    },
  });
}

// Render cumulative EV dollars generated chart
function renderEvDollarsChart(bets) {
  const ctx = document.getElementById("ev-dollars-chart");

  if (!ctx) return;

  // Destroy existing chart
  if (evDollarsChart) {
    evDollarsChart.destroy();
  }

  if (bets.length === 0) {
    evDollarsChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: ["No bets yet"],
        datasets: [],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          title: {
            display: true,
            text: "Place bets to see EV generated",
          },
        },
      },
    });
    return;
  }

  // Sort by date
  const sortedBets = [...bets].sort(
    (a, b) => new Date(a.placed_at) - new Date(b.placed_at)
  );

  // Calculate cumulative EV dollars
  let cumulativeEV = 0;
  const cumulativeEVData = [];
  const individualEVData = [];
  const labels = [];
  const colors = [];

  sortedBets.forEach((bet, index) => {
    const evDollars = bet.expected_value || 0;
    cumulativeEV += evDollars;

    cumulativeEVData.push(cumulativeEV);
    individualEVData.push(evDollars);
    labels.push(`Bet ${index + 1}`);

    // Color code: green for positive EV, red for negative
    colors.push(
      evDollars >= 0 ? "rgba(16, 185, 129, 0.6)" : "rgba(239, 68, 68, 0.6)"
    );
  });

  evDollarsChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Individual EV ($)",
          data: individualEVData,
          backgroundColor: colors,
          borderColor: colors.map((c) => c.replace("0.6", "1")),
          borderWidth: 1,
          yAxisID: "y",
        },
        {
          label: "Cumulative EV ($)",
          data: cumulativeEVData,
          type: "line",
          borderColor: "rgba(59, 130, 246, 1)",
          backgroundColor: "rgba(59, 130, 246, 0.1)",
          tension: 0.4,
          fill: false,
          borderWidth: 2,
          yAxisID: "y1",
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
        tooltip: {
          callbacks: {
            label: function (context) {
              let label = context.dataset.label || "";
              if (label) {
                label += ": ";
              }
              label += "$" + context.parsed.y.toFixed(2);
              return label;
            },
          },
        },
      },
      scales: {
        y: {
          type: "linear",
          display: true,
          position: "left",
          title: {
            display: true,
            text: "Individual EV ($)",
          },
          ticks: {
            callback: function (value) {
              return "$" + value.toFixed(2);
            },
          },
        },
        y1: {
          type: "linear",
          display: true,
          position: "right",
          title: {
            display: true,
            text: "Cumulative EV ($)",
          },
          grid: {
            drawOnChartArea: false,
          },
          ticks: {
            callback: function (value) {
              return "$" + value.toFixed(2);
            },
          },
        },
        x: {
          title: {
            display: true,
            text: "Bet Number",
          },
        },
      },
    },
  });
}

// Render EV vs AV (Expected Value vs Actual Value) chart
function renderEvAvChart(bets) {
  const ctx = document.getElementById("ev-av-chart");

  if (!ctx) return;

  // Destroy existing chart
  if (evAvChart) {
    evAvChart.destroy();
  }

  // Filter for settled bets only (won or lost, not void)
  const settledBets = bets.filter(
    (bet) => bet.status === "won" || bet.status === "lost"
  );

  if (settledBets.length === 0) {
    // Show empty state
    evAvChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: ["No settled bets yet"],
        datasets: [],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            display: false,
          },
          title: {
            display: true,
            text: "Place and settle bets to see EV vs AV comparison",
          },
        },
      },
    });
    return;
  }

  // Sort by date
  const sortedBets = [...settledBets].sort(
    (a, b) => new Date(a.placed_at) - new Date(b.placed_at)
  );

  // Calculate cumulative EV and AV
  let cumulativeEV = 0;
  let cumulativeAV = 0;
  const cumulativeEVData = [];
  const cumulativeAVData = [];
  const labels = [];

  sortedBets.forEach((bet, index) => {
    // Expected Value = (Fair Probability × Payout) - Stake
    // We stored ev_percentage and expected_value
    const expectedProfit = bet.expected_value; // This is already calculated as EV in dollars

    // Actual Value = Actual Return - Stake
    let actualProfit = 0;
    if (bet.status === "won" && bet.actual_return) {
      actualProfit = bet.actual_return - bet.stake;
    } else if (bet.status === "lost") {
      actualProfit = -bet.stake;
    }

    cumulativeEV += expectedProfit;
    cumulativeAV += actualProfit;

    cumulativeEVData.push(cumulativeEV);
    cumulativeAVData.push(cumulativeAV);
    labels.push(`Bet ${index + 1}`);
  });

  evAvChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Expected Value (EV)",
          data: cumulativeEVData,
          borderColor: "rgba(59, 130, 246, 1)",
          backgroundColor: "rgba(59, 130, 246, 0.1)",
          tension: 0.4,
          fill: false,
          borderWidth: 2,
        },
        {
          label: "Actual Value (AV)",
          data: cumulativeAVData,
          borderColor: "rgba(16, 185, 129, 1)",
          backgroundColor: "rgba(16, 185, 129, 0.1)",
          tension: 0.4,
          fill: false,
          borderWidth: 2,
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
        tooltip: {
          callbacks: {
            label: function (context) {
              let label = context.dataset.label || "";
              if (label) {
                label += ": ";
              }
              label += "$" + context.parsed.y.toFixed(2);
              return label;
            },
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: function (value) {
              return "$" + value.toFixed(2);
            },
          },
          title: {
            display: true,
            text: "Cumulative Profit/Loss ($)",
          },
        },
        x: {
          title: {
            display: true,
            text: "Bet Number",
          },
        },
      },
    },
  });
}

// Render CLV tracking chart
function renderClvChart(bets) {
  const ctx = document.getElementById("clv-chart");

  if (!ctx) return;

  // Destroy existing chart
  if (clvChart) {
    clvChart.destroy();
  }

  // Filter for bets with CLV data
  const betsWithClv = bets.filter(
    (bet) => bet.clv !== null && bet.clv !== undefined
  );

  if (betsWithClv.length === 0) {
    // Show empty state
    clvChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: ["No CLV data yet"],
        datasets: [],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            display: false,
          },
          title: {
            display: true,
            text: "Place bets and wait for closing lines to track CLV",
          },
        },
      },
    });
    return;
  }

  // Sort by date
  const sortedBets = [...betsWithClv].sort(
    (a, b) => new Date(a.placed_at) - new Date(b.placed_at)
  );

  // Calculate cumulative CLV
  let cumulativeCLV = 0;
  const cumulativeCLVData = [];
  const individualCLVData = [];
  const labels = [];
  const colors = [];

  sortedBets.forEach((bet, index) => {
    cumulativeCLV += bet.clv;
    cumulativeCLVData.push(cumulativeCLV);
    individualCLVData.push(bet.clv);
    labels.push(`Bet ${index + 1}`);
    // Color code: green for positive CLV, red for negative
    colors.push(
      bet.clv >= 0 ? "rgba(16, 185, 129, 0.6)" : "rgba(239, 68, 68, 0.6)"
    );
  });

  clvChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Individual CLV (%)",
          data: individualCLVData,
          backgroundColor: colors,
          borderColor: colors.map((c) => c.replace("0.6", "1")),
          borderWidth: 1,
          yAxisID: "y",
        },
        {
          label: "Cumulative CLV (%)",
          data: cumulativeCLVData,
          type: "line",
          borderColor: "rgba(168, 85, 247, 1)",
          backgroundColor: "rgba(168, 85, 247, 0.1)",
          tension: 0.4,
          fill: false,
          borderWidth: 2,
          yAxisID: "y1",
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
        tooltip: {
          callbacks: {
            label: function (context) {
              let label = context.dataset.label || "";
              if (label) {
                label += ": ";
              }
              label += context.parsed.y.toFixed(2) + "%";
              return label;
            },
          },
        },
      },
      scales: {
        y: {
          type: "linear",
          display: true,
          position: "left",
          title: {
            display: true,
            text: "Individual CLV (%)",
          },
          ticks: {
            callback: function (value) {
              return value.toFixed(1) + "%";
            },
          },
        },
        y1: {
          type: "linear",
          display: true,
          position: "right",
          title: {
            display: true,
            text: "Cumulative CLV (%)",
          },
          grid: {
            drawOnChartArea: false,
          },
          ticks: {
            callback: function (value) {
              return value.toFixed(1) + "%";
            },
          },
        },
        x: {
          title: {
            display: true,
            text: "Bet Number",
          },
        },
      },
    },
  });
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
