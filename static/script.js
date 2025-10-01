// API Base URL
const API_BASE = window.location.origin;

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  loadStats();
  loadMarkets();
  loadSchedulerStatus();

  // Auto-refresh every 60 seconds
  setInterval(() => {
    loadStats();
    loadMarkets();
    loadSchedulerStatus();
  }, 60000);

  // Check scheduler status more frequently (every 10 seconds)
  setInterval(() => {
    loadSchedulerStatus();
  }, 10000);
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

// Load statistics
async function loadStats() {
  try {
    const response = await fetch(`${API_BASE}/api/stats`);
    const data = await response.json();

    document.getElementById("stat-pinnacle").textContent = data.pinnacle_count;
    document.getElementById("stat-cs500").textContent = data.cs500_count;
    document.getElementById("stat-matched").textContent = data.matched_count;
    document.getElementById("stat-positive").textContent =
      data.positive_ev_count;

    // Update unmatched count
    const unmatchedTotal =
      (data.unmatched_pinnacle_count || 0) + (data.unmatched_cs500_count || 0);
    document.getElementById("unmatched-count").textContent = unmatchedTotal;
  } catch (error) {
    console.error("Failed to load stats:", error);
  }
}

// Load markets
async function loadMarkets() {
  showLoading();

  try {
    const sportFilter = document.getElementById("sport-filter").value;
    const minEv = document.getElementById("min-ev").value;
    const positiveOnly = document.getElementById("positive-only").checked;
    const evMethod = document.getElementById("ev-method").value;

    let url = `${API_BASE}/api/markets?min_ev=${minEv}`;
    if (sportFilter) {
      url += `&sport=${sportFilter}`;
    }

    const response = await fetch(url);
    const data = await response.json();

    let markets = data.markets || [];

    // Filter positive only if checkbox is checked, using selected EV method
    if (positiveOnly) {
      if (evMethod === "mult") {
        markets = markets.filter(
          (m) => m.home_mult_ev_pct > 0 || m.away_mult_ev_pct > 0
        );
      } else {
        markets = markets.filter((m) => m.home_ev_pct > 0 || m.away_ev_pct > 0);
      }
    }

    renderMarkets(markets);
  } catch (error) {
    console.error("Failed to load markets:", error);
    showStatus("Failed to load markets", "error");
  } finally {
    hideLoading();
  }
}

// Store current markets for bet placement
let currentMarkets = [];

// Render markets table
function renderMarkets(markets) {
  const tbody = document.getElementById("markets-body");

  // Store markets globally for bet placement
  currentMarkets = markets;

  if (!markets || markets.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="11" class="no-data">No markets found</td></tr>';
    return;
  }

  // Get selected EV method for sorting
  const evMethod = document.getElementById("ev-method").value;

  // Update the EV column header indicator
  const indicator = document.getElementById("ev-method-indicator");
  if (indicator) {
    indicator.textContent = evMethod === "mult" ? "(Mult)" : "(Power)";
    indicator.style.color = evMethod === "mult" ? "#10b981" : "#3b82f6";
    indicator.style.fontWeight = "bold";
  }

  console.log(`🔄 Sorting by ${evMethod} method`);

  // Sort markets by best EV (highest to lowest) based on selected method
  const sortedMarkets = [...markets].sort((a, b) => {
    let bestEvA, bestEvB;

    if (evMethod === "mult") {
      bestEvA = Math.max(a.home_mult_ev_pct || 0, a.away_mult_ev_pct || 0);
      bestEvB = Math.max(b.home_mult_ev_pct || 0, b.away_mult_ev_pct || 0);
    } else {
      bestEvA = Math.max(a.home_ev_pct || 0, a.away_ev_pct || 0);
      bestEvB = Math.max(b.home_ev_pct || 0, b.away_ev_pct || 0);
    }

    return bestEvB - bestEvA; // Descending order (highest EV first)
  });

  console.log(
    "📊 Top 3 markets after sorting:",
    sortedMarkets.slice(0, 3).map((m) => ({
      teams: `${m.pinnacle_home} vs ${m.pinnacle_away}`,
      power_best: `${Math.max(m.home_ev_pct || 0, m.away_ev_pct || 0).toFixed(
        2
      )}%`,
      mult_best: `${Math.max(
        m.home_mult_ev_pct || 0,
        m.away_mult_ev_pct || 0
      ).toFixed(2)}%`,
    }))
  );

  tbody.innerHTML = sortedMarkets
    .map((market) => {
      const sport = market.sport || "unknown";
      const sportClass = sport === "cs2" ? "sport-cs2" : "sport-lol";
      const sportLabel =
        sport === "cs2" ? "CS2" : sport === "lol" ? "LoL" : sport.toUpperCase();

      // Determine which bet has better EV based on selected method
      let homeEvPct, awayEvPct;
      if (evMethod === "mult") {
        homeEvPct = market.home_mult_ev_pct || 0;
        awayEvPct = market.away_mult_ev_pct || 0;
      } else {
        homeEvPct = market.home_ev_pct || 0;
        awayEvPct = market.away_ev_pct || 0;
      }

      const isBestHome = homeEvPct >= awayEvPct;
      const bestEv = isBestHome ? homeEvPct : awayEvPct;
      const bestSide = isBestHome ? "home" : "away";
      const betTeam = isBestHome ? market.pinnacle_home : market.pinnacle_away;
      const fairOdds = isBestHome ? market.home_fair : market.away_fair;
      const multOdds = isBestHome ? market.home_mult : market.away_mult;
      const cs500Odds = isBestHome
        ? market.cs500_home_odds
        : market.cs500_away_odds;

      // Calculate implied probability from CS500 odds
      const impliedProb = ((1 / cs500Odds) * 100).toFixed(2);

      // Format start time
      let startTime = "TBD";
      if (market.start_time) {
        try {
          const date = new Date(market.start_time);
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

      const evClass = bestEv > 0 ? "ev-positive" : "ev-negative";
      const betClass = bestSide === "home" ? "bet-home" : "bet-away";

      return `
            <tr class="market-row" onclick="openMatchDetailsModal('${
              market.pinnacle_id
            }')" style="cursor: pointer;">
                <td>
                    <span class="sport-badge ${sportClass}">${sportLabel}</span>
                </td>
                <td>${escapeHtml(market.event || "Unknown Event")}</td>
                <td>
                    <div class="team-matchup">
                        <span class="team-name">${escapeHtml(
                          market.pinnacle_home
                        )}</span>
                        <span class="team-vs">vs</span>
                        <span class="team-name">${escapeHtml(
                          market.pinnacle_away
                        )}</span>
                    </div>
                </td>
                <td>${startTime}</td>
                <td>
                    <span class="bet-side ${betClass}">
                        ${escapeHtml(betTeam)}
                    </span>
                </td>
                <td>
                    <div class="odds-display">
                        <span class="odds-value">${
                          fairOdds ? fairOdds.toFixed(2) : "N/A"
                        }</span>
                    </div>
                </td>
                <td>
                    <div class="odds-display">
                        <span class="odds-value">${
                          multOdds ? multOdds.toFixed(2) : "N/A"
                        }</span>
                    </div>
                </td>
                <td>
                    <div class="odds-display">
                        <span class="odds-value">${cs500Odds.toFixed(2)}</span>
                    </div>
                </td>
                <td>
                    <span class="ev-value ${evClass}">${
        bestEv > 0 ? "+" : ""
      }${bestEv.toFixed(2)}%</span>
                </td>
                <td>${impliedProb}%</td>
                <td onclick="event.stopPropagation()">
                    <button class="btn btn-small btn-bet" onclick="openBetModal('${
                      market.pinnacle_id
                    }')">
                        💰 Bet
                    </button>
                </td>
            </tr>
        `;
    })
    .join("");
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Scrape Pinnacle
async function scrapePinnacle() {
  showLoading();
  showStatus("Scraping Pinnacle...", "warning");

  try {
    const response = await fetch(`${API_BASE}/api/scrape/pinnacle`, {
      method: "POST",
    });
    const data = await response.json();

    if (data.status === "success") {
      showStatus(`✓ Scraped ${data.count} Pinnacle markets`, "success");
      loadStats();
    } else {
      showStatus("Failed to scrape Pinnacle", "error");
    }
  } catch (error) {
    console.error("Pinnacle scrape error:", error);
    showStatus("Error scraping Pinnacle", "error");
  } finally {
    hideLoading();
  }
}

// Scrape CS500
async function scrapeCS500Full() {
  showLoading();
  showStatus("🎮 Starting CS500 scrape in background...", "info");

  try {
    const response = await fetch(`${API_BASE}/api/scrape/cs500-full`, {
      method: "POST",
    });
    const data = await response.json();

    if (data.status === "success") {
      showStatus(
        `✓ CS500 scraping started! This will take 1-2 minutes. Check Railway logs for progress.`,
        "success"
      );

      // Auto-refresh after 2 minutes to show new data
      setTimeout(() => {
        showStatus("🔄 Refreshing data...", "info");
        loadStats();
        loadMarkets();
        showStatus(
          "✓ Data refreshed! Check if CS500 markets appeared.",
          "success"
        );
      }, 120000); // 2 minutes
    } else if (data.status === "warning") {
      showStatus(data.message, "warning");
    }
  } catch (error) {
    console.error("Failed to start CS500 scrape:", error);
    showStatus("Failed to start CS500 scrape. Check logs!", "error");
  } finally {
    hideLoading();
  }
}

async function scrapeCS500() {
  showLoading();
  showStatus(
    "Scraping CS500... (Note: Match IDs must be collected first)",
    "warning"
  );

  try {
    const response = await fetch(`${API_BASE}/api/scrape/cs500`, {
      method: "POST",
    });
    const data = await response.json();

    if (data.status === "success") {
      showStatus(`✓ Scraped ${data.count} CS500 markets`, "success");
      loadStats();
    } else if (data.status === "warning") {
      showStatus(data.message, "warning");
    } else {
      showStatus("Failed to scrape CS500", "error");
    }
  } catch (error) {
    console.error("CS500 scrape error:", error);
    showStatus("Error scraping CS500", "error");
  } finally {
    hideLoading();
  }
}

// Match markets
async function matchMarkets() {
  showLoading();
  showStatus("Matching markets...", "warning");

  try {
    const response = await fetch(`${API_BASE}/api/match_markets`, {
      method: "POST",
    });
    const data = await response.json();

    if (data.status === "success") {
      let message = `✓ Matched ${data.matched_count} new markets`;
      if (data.skipped_count > 0) {
        message += ` (${data.skipped_count} already mapped)`;
      }
      showStatus(message, "success");
      loadStats();
      loadMarkets();
    } else {
      showStatus("Failed to match markets", "error");
    }
  } catch (error) {
    console.error("Match error:", error);
    showStatus("Error matching markets", "error");
  } finally {
    hideLoading();
  }
}

// Scrape all and match
async function scrapeAll() {
  showLoading();
  showStatus(
    "Running full scrape and match cycle... This may take a while.",
    "warning"
  );

  try {
    const response = await fetch(`${API_BASE}/api/scrape/all`, {
      method: "POST",
    });
    const data = await response.json();

    if (data.status === "success") {
      const results = data.results;
      let message = "Scraping complete!\n";

      if (results.pinnacle && results.pinnacle.status === "success") {
        message += `\n✓ Pinnacle: ${results.pinnacle.count} markets`;
      }
      if (results.cs500 && results.cs500.status === "success") {
        message += `\n✓ CS500: ${results.cs500.count} markets`;
      }
      if (results.matching && results.matching.status === "success") {
        message += `\n✓ Matched: ${results.matching.matched_count} new`;
        if (results.matching.skipped_count > 0) {
          message += ` (${results.matching.skipped_count} already mapped)`;
        }
      }

      showStatus(message, "success");
      loadStats();
      loadMarkets();
    } else {
      showStatus(
        "Scraping completed with some errors. Check console for details.",
        "warning"
      );
    }
  } catch (error) {
    console.error("Scrape all error:", error);
    showStatus("Error during scraping", "error");
  } finally {
    hideLoading();
  }
}

// Re-match markets with improved algorithm
async function rematchMarkets() {
  showLoading();
  showStatus(
    "Clearing old mappings and re-matching with improved algorithm...",
    "warning"
  );

  try {
    const response = await fetch(`${API_BASE}/api/rematch`, {
      method: "POST",
    });
    const data = await response.json();

    if (data.status === "success") {
      showStatus(
        `✓ Re-matched ${data.matched_count} markets out of ${data.total_pinnacle} Pinnacle markets`,
        "success"
      );
      loadStats();
      loadMarkets();
    } else {
      showStatus("Failed to re-match markets", "error");
    }
  } catch (error) {
    console.error("Re-match error:", error);
    showStatus("Error re-matching markets", "error");
  } finally {
    hideLoading();
  }
}

// Scheduler Control Functions

// Load scheduler status
async function loadSchedulerStatus() {
  try {
    const response = await fetch(`${API_BASE}/api/scheduler/status`);
    const data = await response.json();

    // Update status indicator and text
    const indicator = document.getElementById("scheduler-status-indicator");
    const statusText = document.getElementById("scheduler-status-text");
    const startBtn = document.getElementById("scheduler-start-btn");
    const stopBtn = document.getElementById("scheduler-stop-btn");

    if (data.enabled) {
      indicator.className = "status-dot status-on";
      statusText.textContent = `Running (${data.interval_minutes} min)`;
      startBtn.style.display = "none";
      stopBtn.style.display = "inline-block";
    } else {
      indicator.className = "status-dot status-off";
      statusText.textContent = "Stopped";
      startBtn.style.display = "inline-block";
      stopBtn.style.display = "none";
    }

    // Update last scrape times
    document.getElementById("last-pinnacle-scrape").textContent =
      formatTimestamp(data.last_pinnacle_scrape);
    document.getElementById("last-cs500-scrape").textContent = formatTimestamp(
      data.last_cs500_scrape
    );
    document.getElementById("next-scrape").textContent = formatTimestamp(
      data.next_run
    );
  } catch (error) {
    console.error("Failed to load scheduler status:", error);
  }
}

// Start the scheduler
async function startScheduler() {
  const interval = document.getElementById("scrape-interval").value;

  if (interval < 1 || interval > 60) {
    showStatus("Interval must be between 1 and 60 minutes", "error");
    return;
  }

  try {
    const response = await fetch(
      `${API_BASE}/api/scheduler/start?interval_minutes=${interval}`,
      {
        method: "POST",
      }
    );
    const data = await response.json();

    if (data.status === "success") {
      showStatus(
        `Auto-scraping started (every ${interval} minutes)`,
        "success"
      );
      loadSchedulerStatus();
    } else {
      showStatus("Failed to start auto-scraping", "error");
    }
  } catch (error) {
    console.error("Failed to start scheduler:", error);
    showStatus("Error starting auto-scraping", "error");
  }
}

// Stop the scheduler
async function stopScheduler() {
  try {
    const response = await fetch(`${API_BASE}/api/scheduler/stop`, {
      method: "POST",
    });
    const data = await response.json();

    if (data.status === "success") {
      showStatus("Auto-scraping stopped", "success");
      loadSchedulerStatus();
    } else {
      showStatus("Failed to stop auto-scraping", "error");
    }
  } catch (error) {
    console.error("Failed to stop scheduler:", error);
    showStatus("Error stopping auto-scraping", "error");
  }
}

// Format timestamp for display
function formatTimestamp(timestamp) {
  if (!timestamp) return "Never";

  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = date - now;
    const diffMins = Math.round(diffMs / 60000);

    // If it's in the future (next run)
    if (diffMins > 0) {
      if (diffMins < 60) {
        return `in ${diffMins} min`;
      } else {
        const hours = Math.floor(diffMins / 60);
        const mins = diffMins % 60;
        return `in ${hours}h ${mins}m`;
      }
    }

    // If it's in the past (last run)
    const diffSecs = Math.abs(Math.round(diffMs / 1000));

    if (diffSecs < 60) {
      return `${diffSecs}s ago`;
    } else if (diffSecs < 3600) {
      return `${Math.round(diffSecs / 60)} min ago`;
    } else if (diffSecs < 86400) {
      const hours = Math.floor(diffSecs / 3600);
      const mins = Math.round((diffSecs % 3600) / 60);
      return `${hours}h ${mins}m ago`;
    } else {
      return date.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    }
  } catch (e) {
    return "Invalid";
  }
}

// Unmatched Markets Functions

// Show unmatched markets modal
async function showUnmatchedMarkets() {
  try {
    showLoading();
    const response = await fetch(`${API_BASE}/api/markets/unmatched`);
    const data = await response.json();

    if (data.status === "success") {
      renderUnmatchedMarkets(data);
      document.getElementById("unmatched-modal").style.display = "flex";
    } else {
      showStatus("Failed to load unmatched markets", "error");
    }
  } catch (error) {
    console.error("Failed to load unmatched markets:", error);
    showStatus("Error loading unmatched markets", "error");
  } finally {
    hideLoading();
  }
}

// Close unmatched markets modal
function closeUnmatchedModal() {
  document.getElementById("unmatched-modal").style.display = "none";
}

// Render unmatched markets
function renderUnmatchedMarkets(data) {
  const pinnacleList = document.getElementById("unmatched-pinnacle-list");
  const cs500List = document.getElementById("unmatched-cs500-list");

  // Render Pinnacle unmatched markets
  if (data.pinnacle && data.pinnacle.length > 0) {
    pinnacleList.innerHTML = data.pinnacle
      .map((market) => {
        const sport = market.sport || "unknown";
        const sportClass = sport === "cs2" ? "sport-cs2" : "sport-lol";
        const sportLabel =
          sport === "cs2"
            ? "CS2"
            : sport === "lol"
            ? "LoL"
            : sport.toUpperCase();

        return `
          <div class="unmatched-item">
            <div class="unmatched-item-header">
              <div class="unmatched-item-teams">
                ${escapeHtml(market.home_team)} vs ${escapeHtml(
          market.away_team
        )}
              </div>
              <span class="unmatched-item-sport sport-badge ${sportClass}">${sportLabel}</span>
            </div>
            <div class="unmatched-item-details">
              <div><strong>Event:</strong> ${escapeHtml(
                market.event || "Unknown"
              )}</div>
              <div><strong>ID:</strong> ${escapeHtml(market.id)}</div>
            </div>
            <div class="unmatched-item-odds">
              <span><strong>Home Fair:</strong> ${
                market.home_fair_odds?.toFixed(2) || "N/A"
              }</span>
              <span><strong>Away Fair:</strong> ${
                market.away_fair_odds?.toFixed(2) || "N/A"
              }</span>
            </div>
          </div>
        `;
      })
      .join("");
  } else {
    pinnacleList.innerHTML =
      '<div class="no-unmatched">✓ All Pinnacle markets are matched!</div>';
  }

  // Render CS500 unmatched markets
  if (data.cs500 && data.cs500.length > 0) {
    cs500List.innerHTML = data.cs500
      .map((market) => {
        const sport = market.sport || "unknown";
        const sportClass = sport === "cs2" ? "sport-cs2" : "sport-lol";
        const sportLabel =
          sport === "cs2"
            ? "CS2"
            : sport === "lol"
            ? "LoL"
            : sport.toUpperCase();

        return `
          <div class="unmatched-item">
            <div class="unmatched-item-header">
              <div class="unmatched-item-teams">
                ${escapeHtml(market.home_team)} vs ${escapeHtml(
          market.away_team
        )}
              </div>
              <span class="unmatched-item-sport sport-badge ${sportClass}">${sportLabel}</span>
            </div>
            <div class="unmatched-item-details">
              <div><strong>Event:</strong> ${escapeHtml(
                market.event_name || "Unknown"
              )}</div>
              <div><strong>Match ID:</strong> ${escapeHtml(
                market.match_id
              )}</div>
            </div>
            <div class="unmatched-item-odds">
              <span><strong>Home Odds:</strong> ${
                market.home_odds?.toFixed(2) || "N/A"
              }</span>
              <span><strong>Away Odds:</strong> ${
                market.away_odds?.toFixed(2) || "N/A"
              }</span>
            </div>
          </div>
        `;
      })
      .join("");
  } else {
    cs500List.innerHTML =
      '<div class="no-unmatched">✓ All CS500 markets are matched!</div>';
  }
}

// Close modal when clicking outside
document.addEventListener("click", function (event) {
  const unmatchedModal = document.getElementById("unmatched-modal");
  const betModal = document.getElementById("bet-modal");
  const matchDetailsModal = document.getElementById("match-details-modal");

  if (event.target === unmatchedModal) {
    closeUnmatchedModal();
  }
  if (event.target === betModal) {
    closeBetModal();
  }
  if (event.target === matchDetailsModal) {
    closeMatchDetailsModal();
  }
});

// Bet Placement Functions

let currentBetData = null;

// Open bet modal with market data
function openBetModal(pinnacleId) {
  const market = currentMarkets.find((m) => m.pinnacle_id === pinnacleId);
  if (!market) {
    showStatus("Market not found", "error");
    return;
  }

  // Get selected EV method
  const evMethod = document.getElementById("ev-method").value;

  // Determine which bet has better EV based on selected method
  let homeEvPct, awayEvPct, homeFairOdds, awayFairOdds;
  if (evMethod === "mult") {
    homeEvPct = market.home_mult_ev_pct || 0;
    awayEvPct = market.away_mult_ev_pct || 0;
    homeFairOdds = market.home_mult || market.home_fair;
    awayFairOdds = market.away_mult || market.away_fair;
  } else {
    homeEvPct = market.home_ev_pct || 0;
    awayEvPct = market.away_ev_pct || 0;
    homeFairOdds = market.home_fair;
    awayFairOdds = market.away_fair;
  }

  const isBestHome = homeEvPct >= awayEvPct;
  const betSide = isBestHome ? "home" : "away";
  const betTeam = isBestHome ? market.pinnacle_home : market.pinnacle_away;
  const odds = isBestHome ? market.cs500_home_odds : market.cs500_away_odds;
  const fairOdds = isBestHome ? homeFairOdds : awayFairOdds;
  const evPct = isBestHome ? homeEvPct : awayEvPct;

  // Store bet data
  currentBetData = {
    pinnacle_id: market.pinnacle_id,
    event: market.event,
    sport: market.sport,
    home_team: market.pinnacle_home,
    away_team: market.pinnacle_away,
    bet_side: betSide,
    bet_team: betTeam,
    odds: odds,
    fair_odds: fairOdds,
    ev_percentage: evPct,
    start_time: market.start_time,
  };

  // Update modal content
  document.getElementById(
    "bet-match-info"
  ).textContent = `${market.pinnacle_home} vs ${market.pinnacle_away}`;
  document.getElementById("bet-event").textContent = market.event || "Unknown";
  document.getElementById("bet-team").textContent = betTeam;
  document.getElementById("bet-odds").textContent = odds.toFixed(2);
  document.getElementById("bet-fair-odds").textContent = fairOdds.toFixed(2);
  document.getElementById("bet-ev").textContent = `${
    evPct > 0 ? "+" : ""
  }${evPct.toFixed(2)}%`;

  // Reset stake to default
  document.getElementById("bet-stake").value = "10";
  document.getElementById("bet-notes").value = "";

  // Update calculations
  updateBetCalculations();

  // Show modal
  document.getElementById("bet-modal").style.display = "flex";
}

// Close bet modal
function closeBetModal() {
  document.getElementById("bet-modal").style.display = "none";
  currentBetData = null;
}

// Update bet calculations based on stake
function updateBetCalculations() {
  if (!currentBetData) return;

  const stake = parseFloat(document.getElementById("bet-stake").value) || 0;
  const odds = currentBetData.odds;

  const potentialReturn = stake * odds;
  const potentialProfit = potentialReturn - stake;

  document.getElementById("bet-potential-return").textContent =
    potentialReturn.toFixed(2);
  document.getElementById("bet-potential-profit").textContent =
    potentialProfit.toFixed(2);
}

// Confirm and place bet
async function confirmPlaceBet() {
  if (!currentBetData) {
    showStatus("No bet data available", "error");
    return;
  }

  const stake = parseFloat(document.getElementById("bet-stake").value);
  if (!stake || stake <= 0) {
    showStatus("Please enter a valid stake amount", "error");
    return;
  }

  const notes = document.getElementById("bet-notes").value;
  const fairProb = 1 / currentBetData.fair_odds;
  const expectedValue = fairProb * currentBetData.odds * stake - stake;
  const potentialReturn = stake * currentBetData.odds;
  const potentialProfit = potentialReturn - stake;

  const betRequest = {
    pinnacle_id: currentBetData.pinnacle_id,
    event: currentBetData.event,
    sport: currentBetData.sport,
    home_team: currentBetData.home_team,
    away_team: currentBetData.away_team,
    bet_side: currentBetData.bet_side,
    bet_team: currentBetData.bet_team,
    odds: currentBetData.odds,
    stake: stake,
    expected_value: expectedValue,
    ev_percentage: currentBetData.ev_percentage,
    fair_odds: currentBetData.fair_odds,
    potential_return: potentialReturn,
    potential_profit: potentialProfit,
    start_time: currentBetData.start_time,
    notes: notes || null,
  };

  try {
    showLoading();
    const response = await fetch(`${API_BASE}/api/bets`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(betRequest),
    });

    const data = await response.json();

    if (data.status === "success") {
      showStatus(`✓ Bet placed successfully! (ID: ${data.bet_id})`, "success");
      closeBetModal();
    } else {
      showStatus("Failed to place bet", "error");
    }
  } catch (error) {
    console.error("Failed to place bet:", error);
    showStatus("Error placing bet", "error");
  } finally {
    hideLoading();
  }
}

// Match Details Functions

// Open match details modal
async function openMatchDetailsModal(pinnacleId) {
  try {
    showLoading();
    const response = await fetch(`${API_BASE}/api/match/${pinnacleId}`);
    const data = await response.json();

    if (data.status === "success") {
      renderMatchDetails(data.match);
      document.getElementById("match-details-modal").style.display = "flex";
    } else {
      showStatus("Failed to load match details", "error");
    }
  } catch (error) {
    console.error("Failed to load match details:", error);
    showStatus("Error loading match details", "error");
  } finally {
    hideLoading();
  }
}

// Close match details modal
function closeMatchDetailsModal() {
  document.getElementById("match-details-modal").style.display = "none";
}

// Render match details
function renderMatchDetails(match) {
  const content = document.getElementById("match-details-content");

  const sport = match.sport || "unknown";
  const sportClass = sport === "cs2" ? "sport-cs2" : "sport-lol";
  const sportLabel =
    sport === "cs2" ? "CS2" : sport === "lol" ? "LoL" : sport.toUpperCase();

  // Format start time
  let startTime = "TBD";
  if (match.start_time) {
    try {
      const date = new Date(match.start_time);
      startTime = date.toLocaleString("en-US", {
        weekday: "short",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (e) {
      startTime = "Invalid Date";
    }
  }

  // Check if CS500 data is available
  const hasCS500 = match.cs500_home_odds && match.cs500_away_odds;

  content.innerHTML = `
    <div class="match-details-header">
      <div class="match-details-title">
        <span class="sport-badge ${sportClass}">${sportLabel}</span>
        <h3>${escapeHtml(match.pinnacle_home)} vs ${escapeHtml(
    match.pinnacle_away
  )}</h3>
      </div>
      <div class="match-details-meta">
        <div><strong>Event:</strong> ${escapeHtml(
          match.event || "Unknown"
        )}</div>
        <div><strong>Start Time:</strong> ${startTime}</div>
        ${
          match.confidence_score
            ? `<div><strong>Match Confidence:</strong> ${(
                match.confidence_score * 100
              ).toFixed(1)}%</div>`
            : ""
        }
      </div>
    </div>

    <div class="match-details-grid">
      <!-- Pinnacle (Sharp) Fair Odds Section -->
      <div class="detail-section">
        <h4>📊 Pinnacle Fair Odds (Sharp)</h4>
        <div class="detail-cards">
          <div class="detail-card">
            <div class="detail-card-header">
              <span class="team-label home-label">${escapeHtml(
                match.pinnacle_home
              )}</span>
            </div>
            <div class="detail-card-body">
              <div class="detail-row">
                <span>Power Method (k=1.07):</span>
                <span class="odds-value">${
                  match.home_fair ? match.home_fair.toFixed(2) : "N/A"
                }</span>
              </div>
              <div class="detail-row">
                <span>Probability:</span>
                <span class="prob-value">${match.home_fair_prob}%</span>
              </div>
              <div class="detail-row">
                <span>Multiplicative:</span>
                <span class="odds-value">${
                  match.home_mult ? match.home_mult.toFixed(2) : "N/A"
                }</span>
              </div>
              <div class="detail-row">
                <span>Probability:</span>
                <span class="prob-value">${match.home_mult_prob}%</span>
              </div>
            </div>
          </div>

          <div class="detail-card">
            <div class="detail-card-header">
              <span class="team-label away-label">${escapeHtml(
                match.pinnacle_away
              )}</span>
            </div>
            <div class="detail-card-body">
              <div class="detail-row">
                <span>Power Method (k=1.07):</span>
                <span class="odds-value">${
                  match.away_fair ? match.away_fair.toFixed(2) : "N/A"
                }</span>
              </div>
              <div class="detail-row">
                <span>Probability:</span>
                <span class="prob-value">${match.away_fair_prob}%</span>
              </div>
              <div class="detail-row">
                <span>Multiplicative:</span>
                <span class="odds-value">${
                  match.away_mult ? match.away_mult.toFixed(2) : "N/A"
                }</span>
              </div>
              <div class="detail-row">
                <span>Probability:</span>
                <span class="prob-value">${match.away_mult_prob}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      ${
        hasCS500
          ? `
      <!-- CS500 (Soft Book) Section -->
      <div class="detail-section">
        <h4>🎮 CS500 Odds (Soft Book)</h4>
        <div class="detail-cards">
          <div class="detail-card">
            <div class="detail-card-header">
              <span class="team-label home-label">${escapeHtml(
                match.cs500_home || match.pinnacle_home
              )}</span>
            </div>
            <div class="detail-card-body">
              <div class="detail-row">
                <span>Odds:</span>
                <span class="odds-value">${match.cs500_home_odds.toFixed(
                  2
                )}</span>
              </div>
              <div class="detail-row">
                <span>Implied Probability:</span>
                <span class="prob-value">${match.cs500_home_prob}%</span>
              </div>
            </div>
          </div>

          <div class="detail-card">
            <div class="detail-card-header">
              <span class="team-label away-label">${escapeHtml(
                match.cs500_away || match.pinnacle_away
              )}</span>
            </div>
            <div class="detail-card-body">
              <div class="detail-row">
                <span>Odds:</span>
                <span class="odds-value">${match.cs500_away_odds.toFixed(
                  2
                )}</span>
              </div>
              <div class="detail-row">
                <span>Implied Probability:</span>
                <span class="prob-value">${match.cs500_away_prob}%</span>
              </div>
            </div>
          </div>
        </div>
        <div class="detail-info-box">
          <div class="detail-info-item">
            <span>Total Implied Probability:</span>
            <span>${match.cs500_total_prob}%</span>
          </div>
          <div class="detail-info-item">
            <span>Vigorish (Vig):</span>
            <span>${match.cs500_vig}%</span>
          </div>
        </div>
      </div>

      <!-- Expected Value (EV) Analysis -->
      <div class="detail-section full-width">
        <h4>💰 Expected Value (EV) Analysis</h4>
        
        <div class="ev-method-section">
          <h5>Power Method (k=1.07)</h5>
          <div class="detail-cards">
            <div class="detail-card ${
              match.home_ev_pct > 0 ? "ev-positive-card" : "ev-negative-card"
            }">
              <div class="detail-card-header">
                <span class="team-label home-label">${escapeHtml(
                  match.pinnacle_home
                )}</span>
                ${
                  match.best_bet_power === "home"
                    ? '<span class="best-bet-badge">🔥 Best Bet</span>'
                    : ""
                }
              </div>
              <div class="detail-card-body">
                <div class="detail-row">
                  <span>Expected Value:</span>
                  <span class="ev-value ${
                    match.home_ev_pct > 0 ? "ev-positive" : "ev-negative"
                  }">
                    ${match.home_ev_pct > 0 ? "+" : ""}${match.home_ev_pct}%
                  </span>
                </div>
                <div class="detail-row">
                  <span>Raw EV:</span>
                  <span class="odds-value">${
                    match.home_ev ? match.home_ev.toFixed(4) : "N/A"
                  }</span>
                </div>
                <div class="detail-row">
                  <span>Fair Probability:</span>
                  <span class="prob-value">${match.home_fair_prob}%</span>
                </div>
                <div class="detail-row">
                  <span>CS500 Odds:</span>
                  <span class="odds-value">${match.cs500_home_odds.toFixed(
                    2
                  )}</span>
                </div>
              </div>
            </div>

            <div class="detail-card ${
              match.away_ev_pct > 0 ? "ev-positive-card" : "ev-negative-card"
            }">
              <div class="detail-card-header">
                <span class="team-label away-label">${escapeHtml(
                  match.pinnacle_away
                )}</span>
                ${
                  match.best_bet_power === "away"
                    ? '<span class="best-bet-badge">🔥 Best Bet</span>'
                    : ""
                }
              </div>
              <div class="detail-card-body">
                <div class="detail-row">
                  <span>Expected Value:</span>
                  <span class="ev-value ${
                    match.away_ev_pct > 0 ? "ev-positive" : "ev-negative"
                  }">
                    ${match.away_ev_pct > 0 ? "+" : ""}${match.away_ev_pct}%
                  </span>
                </div>
                <div class="detail-row">
                  <span>Raw EV:</span>
                  <span class="odds-value">${
                    match.away_ev ? match.away_ev.toFixed(4) : "N/A"
                  }</span>
                </div>
                <div class="detail-row">
                  <span>Fair Probability:</span>
                  <span class="prob-value">${match.away_fair_prob}%</span>
                </div>
                <div class="detail-row">
                  <span>CS500 Odds:</span>
                  <span class="odds-value">${match.cs500_away_odds.toFixed(
                    2
                  )}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="ev-method-section">
          <h5>Multiplicative Method</h5>
          <div class="detail-cards">
            <div class="detail-card ${
              match.home_mult_ev_pct > 0
                ? "ev-positive-card"
                : "ev-negative-card"
            }">
              <div class="detail-card-header">
                <span class="team-label home-label">${escapeHtml(
                  match.pinnacle_home
                )}</span>
                ${
                  match.best_bet_mult === "home"
                    ? '<span class="best-bet-badge">🔥 Best Bet</span>'
                    : ""
                }
              </div>
              <div class="detail-card-body">
                <div class="detail-row">
                  <span>Expected Value:</span>
                  <span class="ev-value ${
                    match.home_mult_ev_pct > 0 ? "ev-positive" : "ev-negative"
                  }">
                    ${match.home_mult_ev_pct > 0 ? "+" : ""}${
              match.home_mult_ev_pct
            }%
                  </span>
                </div>
                <div class="detail-row">
                  <span>Raw EV:</span>
                  <span class="odds-value">${
                    match.home_mult_ev ? match.home_mult_ev.toFixed(4) : "N/A"
                  }</span>
                </div>
                <div class="detail-row">
                  <span>Fair Probability:</span>
                  <span class="prob-value">${match.home_mult_prob}%</span>
                </div>
                <div class="detail-row">
                  <span>CS500 Odds:</span>
                  <span class="odds-value">${match.cs500_home_odds.toFixed(
                    2
                  )}</span>
                </div>
              </div>
            </div>

            <div class="detail-card ${
              match.away_mult_ev_pct > 0
                ? "ev-positive-card"
                : "ev-negative-card"
            }">
              <div class="detail-card-header">
                <span class="team-label away-label">${escapeHtml(
                  match.pinnacle_away
                )}</span>
                ${
                  match.best_bet_mult === "away"
                    ? '<span class="best-bet-badge">🔥 Best Bet</span>'
                    : ""
                }
              </div>
              <div class="detail-card-body">
                <div class="detail-row">
                  <span>Expected Value:</span>
                  <span class="ev-value ${
                    match.away_mult_ev_pct > 0 ? "ev-positive" : "ev-negative"
                  }">
                    ${match.away_mult_ev_pct > 0 ? "+" : ""}${
              match.away_mult_ev_pct
            }%
                  </span>
                </div>
                <div class="detail-row">
                  <span>Raw EV:</span>
                  <span class="odds-value">${
                    match.away_mult_ev ? match.away_mult_ev.toFixed(4) : "N/A"
                  }</span>
                </div>
                <div class="detail-row">
                  <span>Fair Probability:</span>
                  <span class="prob-value">${match.away_mult_prob}%</span>
                </div>
                <div class="detail-row">
                  <span>CS500 Odds:</span>
                  <span class="odds-value">${match.cs500_away_odds.toFixed(
                    2
                  )}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      `
          : `
      <div class="detail-section full-width">
        <div class="no-cs500-data">
          <p>⚠️ No CS500 data available for this match</p>
          <p class="text-small">This match hasn't been matched with CS500 yet or CS500 doesn't have odds for it.</p>
        </div>
      </div>
      `
      }
    </div>
  `;
}
