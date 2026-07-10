import os
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def build_dashboard():
    comparison_file = "final_comparison.json"
    processed_dir = "data/processed"
    
    if not os.path.exists(comparison_file):
        logging.error(f"File {comparison_file} not found. Please run the pipeline first.")
        return
        
    with open(comparison_file, "r", encoding="utf-8") as f:
        comp_data = json.load(f)
        
    m1 = comp_data["model_1"]
    m2 = comp_data["model_2"]
    
    m1_name = m1["model_name"]
    m2_name = m2["model_name"]
    
    records_m1 = m1["raw_records"]
    records_m2 = m2["raw_records"]
    
    # Map predictions by match_id and freeze_minute
    predictions = {}
    
    # Process Model 1 (Qwen)
    for r in records_m1:
        match_id = r["match_id"]
        minute = r["freeze_minute"]
        if match_id not in predictions:
            predictions[match_id] = {}
        if minute not in predictions[match_id]:
            predictions[match_id][minute] = {}
        predictions[match_id][minute]["model_1"] = {
            "predictions": r["predictions"],
            "grades": r["grades"]
        }
        
    # Process Model 2 (Gemma)
    for r in records_m2:
        match_id = r["match_id"]
        minute = r["freeze_minute"]
        if match_id not in predictions:
            predictions[match_id] = {}
        if minute not in predictions[match_id]:
            predictions[match_id][minute] = {}
        predictions[match_id][minute]["model_2"] = {
            "predictions": r["predictions"],
            "grades": r["grades"]
        }
        
    dashboard_matches = []
    
    for match_id, mins in predictions.items():
        match_file = os.path.join(processed_dir, f"{match_id}.json")
        if not os.path.exists(match_file):
            logging.warning(f"Processed match file {match_file} not found, skipping match {match_id}")
            continue
            
        with open(match_file, "r", encoding="utf-8") as f:
            match_data = json.load(f)
            
        home = match_data["home_team"]
        away = match_data["away_team"]
        events = match_data["events"]
        
        match_entry = {
            "match_id": match_id,
            "home_team": home,
            "away_team": away,
            "events": events,
            "predictions": mins
        }
        dashboard_matches.append(match_entry)
        
    # HTML Template
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pulse: In-Play Match Reasoning Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #f1f5f9;
            --sidebar-bg: #ffffff;
            --card-bg: #ffffff;
            --border-color: #e2e8f0;
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --accent-blue: #2563eb;
            --accent-purple: #7c3aed;
            --accent-green: #059669;
            --accent-red: #dc2626;
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.05);
            --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
            --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.05), 0 4px 6px -2px rgba(0,0,0,0.03);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            display: flex;
            height: 100vh;
            overflow: hidden;
        }

        /* Sidebar styling */
        .sidebar {
            width: 320px;
            background-color: var(--sidebar-bg);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            height: 100%;
        }

        .sidebar-header {
            padding: 1.75rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .logo-dot {
            width: 8px;
            height: 8px;
            background-color: var(--accent-blue);
            border-radius: 50%;
        }

        .logo-text {
            font-family: 'Outfit', sans-serif;
            font-size: 1.25rem;
            font-weight: 800;
            letter-spacing: 0.05rem;
            background: linear-gradient(135deg, var(--text-primary) 30%, var(--accent-blue) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .match-list {
            flex-grow: 1;
            overflow-y: auto;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }

        .match-item {
            background-color: #f8fafc;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .match-item:hover {
            border-color: var(--accent-blue);
            box-shadow: var(--shadow-sm);
            transform: translateY(-1px);
        }

        .match-item.active {
            background-color: rgba(37, 99, 235, 0.04);
            border-color: var(--accent-blue);
            box-shadow: var(--shadow-sm);
        }

        .match-item-teams {
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            font-size: 1rem;
            margin-bottom: 0.25rem;
        }

        .match-item-meta {
            font-size: 0.8rem;
            color: var(--text-secondary);
        }

        /* Main content area */
        .main-content {
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            height: 100%;
            overflow: hidden;
        }

        .dashboard-header {
            background-color: #ffffff;
            border-bottom: 1px solid var(--border-color);
            padding: 1.5rem 2.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .match-title {
            font-family: 'Outfit', sans-serif;
            font-size: 1.75rem;
            font-weight: 800;
        }

        /* Minute Control Tabs */
        .minute-selector {
            display: flex;
            background: #f1f5f9;
            border-radius: 12px;
            padding: 0.3rem;
            gap: 0.25rem;
        }

        .minute-btn {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            font-size: 0.95rem;
            padding: 0.5rem 1.25rem;
            border-radius: 9px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .minute-btn.active {
            background: #ffffff;
            color: var(--accent-blue);
            box-shadow: var(--shadow-sm);
        }

        /* Dashboard Body Layout */
        .dashboard-body {
            flex-grow: 1;
            padding: 2.5rem;
            overflow-y: auto;
            display: grid;
            grid-template-columns: 1.1fr 1.9fr;
            gap: 2rem;
        }

        .left-col {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .right-col {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        /* Widgets/Cards styling */
        .widget-card {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.75rem;
            box-shadow: var(--shadow-sm);
        }

        .widget-title {
            font-family: 'Outfit', sans-serif;
            font-size: 1.15rem;
            font-weight: 600;
            margin-bottom: 1.25rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        /* Scoreboard styling */
        .scoreboard {
            display: flex;
            justify-content: space-between;
            align-items: center;
            text-align: center;
        }

        .score-team {
            width: 40%;
        }

        .team-name {
            font-family: 'Outfit', sans-serif;
            font-weight: 800;
            font-size: 1.25rem;
            margin-top: 0.5rem;
        }

        .score-display {
            font-family: 'Outfit', sans-serif;
            font-size: 2.5rem;
            font-weight: 800;
            background: #f8fafc;
            border: 1px solid var(--border-color);
            padding: 0.5rem 1.5rem;
            border-radius: 12px;
            letter-spacing: 0.1rem;
        }

        /* Timeline styling */
        .timeline {
            display: flex;
            flex-direction: column;
            gap: 1rem;
            position: relative;
            padding-left: 1rem;
        }

        .timeline::before {
            content: '';
            position: absolute;
            left: 1.25rem;
            top: 0.5rem;
            bottom: 0.5rem;
            width: 2px;
            background-color: var(--border-color);
        }

        .timeline-event {
            display: flex;
            align-items: flex-start;
            position: relative;
            padding-left: 1.5rem;
        }

        .timeline-dot {
            position: absolute;
            left: 0;
            top: 0.25rem;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: var(--text-secondary);
            border: 2px solid #ffffff;
            box-shadow: 0 0 0 2px var(--border-color);
            z-index: 1;
        }

        .timeline-dot.goal {
            background-color: var(--accent-green);
        }

        .timeline-dot.card {
            background-color: #eab308;
        }

        .event-time {
            font-family: monospace;
            font-weight: 700;
            font-size: 0.9rem;
            color: var(--text-secondary);
            min-width: 40px;
        }

        .event-desc {
            font-size: 0.9rem;
            color: var(--text-primary);
        }

        /* Model Comparison Columns */
        .arena-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1.5rem;
        }

        .model-col-header {
            font-family: 'Outfit', sans-serif;
            font-weight: 800;
            font-size: 1.2rem;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .model-qwen {
            color: var(--accent-blue);
        }

        .model-gemma {
            color: var(--accent-purple);
        }

        .read-box {
            background-color: #f8fafc;
            border-left: 4px solid var(--accent-blue);
            padding: 1rem;
            border-radius: 0 12px 12px 0;
            font-size: 0.95rem;
            line-height: 1.5;
            color: var(--text-secondary);
            margin-bottom: 1.25rem;
            min-height: 100px;
        }

        .gemma-read {
            border-left-color: var(--accent-purple);
        }

        /* Prediction Bar styling */
        .metric-row {
            margin-bottom: 1rem;
        }

        .metric-meta {
            display: flex;
            justify-content: space-between;
            font-size: 0.9rem;
            margin-bottom: 0.35rem;
        }

        .metric-name {
            font-weight: 600;
            color: var(--text-primary);
        }

        .metric-val {
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
        }

        .bar-outer {
            width: 100%;
            height: 8px;
            background: #f1f5f9;
            border-radius: 4px;
            overflow: hidden;
        }

        .bar-inner {
            height: 100%;
            border-radius: 4px;
            transition: width 0.4s ease;
        }

        .qwen-bar {
            background-color: var(--accent-blue);
        }

        .gemma-bar {
            background-color: var(--accent-purple);
        }

        /* Grading Badge */
        .grade-card {
            border-radius: 12px;
            padding: 1rem;
            margin-top: 1.25rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-weight: 600;
        }

        .grade-card.correct {
            background-color: rgba(5, 150, 105, 0.08);
            border: 1px solid rgba(5, 150, 105, 0.2);
            color: var(--accent-green);
        }

        .grade-card.incorrect {
            background-color: rgba(220, 38, 38, 0.08);
            border: 1px solid rgba(220, 38, 38, 0.2);
            color: var(--accent-red);
        }

        /* What Happened Next Widget */
        .future-badge-container {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-top: 0.5rem;
        }

        .future-badge {
            background: #f8fafc;
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 0.3rem 0.8rem;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }

        .empty-timeline {
            text-align: center;
            color: var(--text-secondary);
            font-size: 0.9rem;
            padding: 1.5rem 0;
        }
    </style>
</head>
<body>

    <!-- Sidebar: Match Selector -->
    <div class="sidebar">
        <div class="sidebar-header">
            <div class="logo-dot"></div>
            <div class="logo-text">PULSE ARENA</div>
        </div>
        <div class="match-list" id="matchList">
            <!-- Matches will be populated by JS -->
        </div>
    </div>

    <!-- Main Dashboard Viewport -->
    <div class="main-content">
        <!-- Header: Match and Minute Controller -->
        <div class="dashboard-header">
            <div class="match-title" id="activeMatchTitle">Select a Match</div>
            <div class="minute-selector">
                <button class="minute-btn active" onclick="setMinute(20)">20'</button>
                <button class="minute-btn" onclick="setMinute(45)">45'</button>
                <button class="minute-btn" onclick="setMinute(70)">70'</button>
            </div>
        </div>

        <!-- Scrollable Dashboard Body -->
        <div class="dashboard-body">
            
            <!-- Left Column: Match State & Timeline -->
            <div class="left-col">
                <!-- Scoreboard Widget -->
                <div class="widget-card">
                    <div class="widget-title">Live Scoreboard</div>
                    <div class="scoreboard">
                        <div class="score-team">
                            <div class="team-name" id="homeTeamName">-</div>
                        </div>
                        <div class="score-display" id="liveScore">0 - 0</div>
                        <div class="score-team">
                            <div class="team-name" id="awayTeamName">-</div>
                        </div>
                    </div>
                </div>

                <!-- Events So Far Timeline Widget -->
                <div class="widget-card" style="flex-grow: 1; display: flex; flex-direction: column;">
                    <div class="widget-title" id="timelineTitle">Timeline (Up to 20')</div>
                    <div style="flex-grow: 1; overflow-y: auto;">
                        <div class="timeline" id="eventsTimeline">
                            <!-- Events will be populated by JS -->
                        </div>
                    </div>
                </div>
            </div>

            <!-- Right Column: Model predictions Side-by-Side -->
            <div class="right-col">
                <!-- Model Battle Arena -->
                <div class="arena-grid">
                    
                    <!-- Qwen Column -->
                    <div>
                        <div class="model-col-header model-qwen">
                            Qwen3.6-27B
                        </div>
                        <div class="widget-card">
                            <div class="read-box" id="qwenRead">
                                No read loaded.
                            </div>
                            
                            <!-- Next Goal -->
                            <div class="metric-row">
                                <div class="metric-meta">
                                    <span class="metric-name">Next Goal Prediction</span>
                                    <span class="metric-val" id="qwenNextGoalVal">-</span>
                                </div>
                                <div class="bar-outer">
                                    <div class="bar-inner qwen-bar" id="qwenNextGoalBar" style="width: 0%"></div>
                                </div>
                            </div>

                            <!-- Next Chance -->
                            <div class="metric-row">
                                <div class="metric-meta">
                                    <span class="metric-name">Next Chance Prediction</span>
                                    <span class="metric-val" id="qwenNextChanceVal">-</span>
                                </div>
                                <div class="bar-outer">
                                    <div class="bar-inner qwen-bar" id="qwenNextChanceBar" style="width: 0%"></div>
                                </div>
                            </div>

                            <!-- Final Result -->
                            <div class="metric-row">
                                <div class="metric-meta">
                                    <span class="metric-name">Final Result prediction</span>
                                    <span class="metric-val" id="qwenFinalResultVal">-</span>
                                </div>
                                <div class="bar-outer">
                                    <div class="bar-inner qwen-bar" id="qwenFinalResultBar" style="width: 0%"></div>
                                </div>
                            </div>

                            <!-- Grader Status -->
                            <div class="grade-card" id="qwenGradeCard">
                                <span>Outcome status</span>
                                <span id="qwenGradeVal">-</span>
                            </div>
                        </div>
                    </div>

                    <!-- Gemma Column -->
                    <div>
                        <div class="model-col-header model-gemma">
                            Gemma-4-31B
                        </div>
                        <div class="widget-card">
                            <div class="read-box gemma-read" id="gemmaRead">
                                No read loaded.
                            </div>
                            
                            <!-- Next Goal -->
                            <div class="metric-row">
                                <div class="metric-meta">
                                    <span class="metric-name">Next Goal Prediction</span>
                                    <span class="metric-val" id="gemmaNextGoalVal">-</span>
                                </div>
                                <div class="bar-outer">
                                    <div class="bar-inner gemma-bar" id="gemmaNextGoalBar" style="width: 0%"></div>
                                </div>
                            </div>

                            <!-- Next Chance -->
                            <div class="metric-row">
                                <div class="metric-meta">
                                    <span class="metric-name">Next Chance Prediction</span>
                                    <span class="metric-val" id="gemmaNextChanceVal">-</span>
                                </div>
                                <div class="bar-outer">
                                    <div class="bar-inner gemma-bar" id="gemmaNextChanceBar" style="width: 0%"></div>
                                </div>
                            </div>

                            <!-- Final Result -->
                            <div class="metric-row">
                                <div class="metric-meta">
                                    <span class="metric-name">Final Result prediction</span>
                                    <span class="metric-val" id="gemmaFinalResultVal">-</span>
                                </div>
                                <div class="bar-outer">
                                    <div class="bar-inner gemma-bar" id="gemmaFinalResultBar" style="width: 0%"></div>
                                </div>
                            </div>

                            <!-- Grader Status -->
                            <div class="grade-card" id="gemmaGradeCard">
                                <span>Outcome status</span>
                                <span id="gemmaGradeVal">-</span>
                            </div>
                        </div>
                    </div>

                </div>

                <!-- What Happened Next Widget -->
                <div class="widget-card">
                    <div class="widget-title">What Happened Next? (Remaining Match Events)</div>
                    <div id="futureEventsBox">
                        <!-- Future events will be populated by JS -->
                    </div>
                </div>
            </div>

        </div>
    </div>

    <!-- Pre-embedded JSON match data -->
    <script>
        const MATCHES_DATA = DATA_PLACEHOLDER;
        
        let activeMatchIdx = 0;
        let activeMinute = 20;

        function initDashboard() {
            const listContainer = document.getElementById("matchList");
            listContainer.innerHTML = "";
            
            MATCHES_DATA.forEach((match, idx) => {
                const item = document.createElement("div");
                item.className = `match-item ${idx === activeMatchIdx ? "active" : ""}`;
                item.onclick = () => selectMatch(idx);
                
                item.innerHTML = `
                    <div class="match-item-teams">${match.home_team} vs ${match.away_team}</div>
                    <div class="match-item-meta">Match ID: ${match.match_id} | ${match.events.length} Key Events</div>
                `;
                listContainer.appendChild(item);
            });
            
            renderActiveMatch();
        }

        function selectMatch(idx) {
            activeMatchIdx = idx;
            document.querySelectorAll(".match-item").forEach((el, i) => {
                el.className = `match-item ${i === activeMatchIdx ? "active" : ""}`;
            });
            renderActiveMatch();
        }

        function setMinute(min) {
            activeMinute = min;
            document.querySelectorAll(".minute-btn").forEach((btn) => {
                const isMatch = parseInt(btn.innerText) === min;
                btn.className = `minute-btn ${isMatch ? "active" : ""}`;
            });
            renderActiveMatch();
        }

        function calculateScoreAtMinute(events, targetMin) {
            let homeGoals = 0;
            let awayGoals = 0;
            events.forEach(e => {
                if (e.minute <= targetMin && e.type === "Goal") {
                    if (e.team === MATCHES_DATA[activeMatchIdx].home_team) {
                        homeGoals++;
                    } else {
                        awayGoals++;
                    }
                }
            });
            return `${homeGoals} - ${awayGoals}`;
        }

        function getFormatPredictionName(teamVal, homeName, awayName) {
            if (teamVal === "home") return homeName;
            if (teamVal === "away") return awayName;
            if (teamVal === "no_more_goals") return "No More Goals";
            if (teamVal === "home_win") return `${homeName} Win`;
            if (teamVal === "away_win") return `${awayName} Win`;
            if (teamVal === "draw") return "Draw";
            return teamVal;
        }

        function renderActiveMatch() {
            const match = MATCHES_DATA[activeMatchIdx];
            if (!match) return;

            document.getElementById("activeMatchTitle").innerText = `${match.home_team} vs ${match.away_team}`;
            document.getElementById("homeTeamName").innerText = match.home_team;
            document.getElementById("awayTeamName").innerText = match.away_team;
            
            // Calculate Score
            document.getElementById("liveScore").innerText = calculateScoreAtMinute(match.events, activeMinute);
            
            // Render Timeline (Up to activeMinute)
            document.getElementById("timelineTitle").innerText = `Timeline (Up to ${activeMinute}')`;
            const timelineContainer = document.getElementById("eventsTimeline");
            timelineContainer.innerHTML = "";
            
            const pastEvents = match.events.filter(e => e.minute <= activeMinute);
            if (pastEvents.length === 0) {
                timelineContainer.innerHTML = `<div class="empty-timeline">No events recorded up to ${activeMinute}'</div>`;
            } else {
                pastEvents.forEach(e => {
                    const row = document.createElement("div");
                    row.className = "timeline-event";
                    
                    let dotClass = "";
                    if (e.type === "Goal") dotClass = "goal";
                    else if (e.type === "Card") dotClass = "card";
                    
                    row.innerHTML = `
                        <div class="timeline-dot ${dotClass}"></div>
                        <div class="event-time">${e.minute}:${e.second.toString().padStart(2, '0')}</div>
                        <div class="event-desc">
                            <strong>${e.team}</strong> | ${e.type}${e.player ? ` (${e.player})` : ""}${e.details ? ` - ${e.details}` : ""}
                        </div>
                    `;
                    timelineContainer.appendChild(row);
                });
            }

            // Render Future Events (What Happened Next)
            const futureContainer = document.getElementById("futureEventsBox");
            futureContainer.innerHTML = "";
            const futureEvents = match.events.filter(e => e.minute > activeMinute);
            
            if (futureEvents.length === 0) {
                futureContainer.innerHTML = `<div class="empty-timeline">No remaining events (Match is finished)</div>`;
            } else {
                const badgeBox = document.createElement("div");
                badgeBox.className = "future-badge-container";
                
                futureEvents.forEach(e => {
                    const badge = document.createElement("div");
                    badge.className = "future-badge";
                    let icon = "⚽";
                    if (e.type === "Card") icon = "🟨/🟥";
                    else if (e.type === "Substitution") icon = "🔄";
                    badge.innerText = `${icon} [${e.minute}'] ${e.team} - ${e.type}${e.player ? ` (${e.player})` : ""}`;
                    badgeBox.appendChild(badge);
                });
                futureContainer.appendChild(badgeBox);
            }

            // Render Predictions
            const minutePredictions = match.predictions[activeMinute.toString()];
            if (minutePredictions) {
                // Qwen (Model 1)
                const qwen = minutePredictions.model_1;
                if (qwen) {
                    const p = qwen.predictions;
                    const g = qwen.grades;
                    
                    document.getElementById("qwenRead").innerText = p.situational_read || "No read available.";
                    
                    // Next Goal
                    const nGoalName = getFormatPredictionName(p.next_goal, match.home_team, match.away_team);
                    document.getElementById("qwenNextGoalVal").innerText = `${nGoalName} (${Math.round(p.next_goal_confidence * 100)}%)`;
                    document.getElementById("qwenNextGoalBar").style.width = `${p.next_goal_confidence * 100}%`;
                    
                    // Next Chance
                    const nChanceName = getFormatPredictionName(p.next_clear_chance, match.home_team, match.away_team);
                    document.getElementById("qwenNextChanceVal").innerText = `${nChanceName} (${Math.round(p.next_clear_chance_confidence * 100)}%)`;
                    document.getElementById("qwenNextChanceBar").style.width = `${p.next_clear_chance_confidence * 100}%`;

                    // Final Result
                    const finalResultName = getFormatPredictionName(p.final_result, match.home_team, match.away_team);
                    document.getElementById("qwenFinalResultVal").innerText = `${finalResultName} (${Math.round(p.final_result_confidence * 100)}%)`;
                    document.getElementById("qwenFinalResultBar").style.width = `${p.final_result_confidence * 100}%`;

                    // Grade Card
                    const isCorrect = g.final_result_grade === 1;
                    const card = document.getElementById("qwenGradeCard");
                    const label = document.getElementById("qwenGradeVal");
                    
                    card.className = `grade-card ${isCorrect ? "correct" : "incorrect"}`;
                    label.innerText = isCorrect ? `Correct (Actual: ${getFormatPredictionName(g.actual.final_result, match.home_team, match.away_team)})` : `Incorrect (Actual: ${getFormatPredictionName(g.actual.final_result, match.home_team, match.away_team)})`;
                }

                // Gemma (Model 2)
                const gemma = minutePredictions.model_2;
                if (gemma) {
                    const p = gemma.predictions;
                    const g = gemma.grades;
                    
                    document.getElementById("gemmaRead").innerText = p.situational_read || "No read available.";
                    
                    // Next Goal
                    const nGoalName = getFormatPredictionName(p.next_goal, match.home_team, match.away_team);
                    document.getElementById("gemmaNextGoalVal").innerText = `${nGoalName} (${Math.round(p.next_goal_confidence * 100)}%)`;
                    document.getElementById("gemmaNextGoalBar").style.width = `${p.next_goal_confidence * 100}%`;
                    
                    // Next Chance
                    const nChanceName = getFormatPredictionName(p.next_clear_chance, match.home_team, match.away_team);
                    document.getElementById("gemmaNextChanceVal").innerText = `${nChanceName} (${Math.round(p.next_clear_chance_confidence * 100)}%)`;
                    document.getElementById("gemmaNextChanceBar").style.width = `${p.next_clear_chance_confidence * 100}%`;

                    // Final Result
                    const finalResultName = getFormatPredictionName(p.final_result, match.home_team, match.away_team);
                    document.getElementById("gemmaFinalResultVal").innerText = `${finalResultName} (${Math.round(p.final_result_confidence * 100)}%)`;
                    document.getElementById("gemmaFinalResultBar").style.width = `${p.final_result_confidence * 100}%`;

                    // Grade Card
                    const isCorrect = g.final_result_grade === 1;
                    const card = document.getElementById("gemmaGradeCard");
                    const label = document.getElementById("gemmaGradeVal");
                    
                    card.className = `grade-card ${isCorrect ? "correct" : "incorrect"}`;
                    label.innerText = isCorrect ? `Correct (Actual: ${getFormatPredictionName(g.actual.final_result, match.home_team, match.away_team)})` : `Incorrect (Actual: ${getFormatPredictionName(g.actual.final_result, match.home_team, match.away_team)})`;
                }
            }
        }

        window.onload = initDashboard;
    </script>
</body>
</html>
"""
    
    # Format and insert the data placeholder
    json_string = json.dumps(dashboard_matches, ensure_ascii=False, indent=4)
    final_html = html_template.replace("DATA_PLACEHOLDER", json_string)
    
    output_html_file = "dashboard.html"
    with open(output_html_file, "w", encoding="utf-8") as f:
        f.write(final_html)
        
    logging.info(f"Dashboard successfully generated and written to {output_html_file}!")

if __name__ == "__main__":
    build_dashboard()
