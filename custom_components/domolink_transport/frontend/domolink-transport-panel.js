/**
 * DomoLink-Transport - Panneau Latéral & Carte Lovelace Officiels
 * Affiche les prochains trains et derniers retours de nuit sous forme de panneau de gare
 * (Mode Moderne Infogare TFT & Mode Mécanique Palettes Solari).
 * Version: 1.0.11
 * Repo: https://github.com/SocrateMobile/Domolink-transport
 */

const VERSION = "1.0.11";
const GITHUB_REPO = "SocrateMobile/Domolink-transport";

class DomolinkTransportPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._styleMode = localStorage.getItem("domolink_transport_style") || "modern"; // "modern" ou "mechanical"
    this._initialized = false;
    this._data = null;
    this._logoClickCount = 0;
    this._logoClickTimer = null;
    this._updateInfo = null;
    this._installedVersion = VERSION;
  }

  set panel(panel) {
    this._panel = panel;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._initialized) {
      this._initialized = true;
      this._renderLayout();
      this._fetchData();
      this._checkUpdate();
    }
  }

  connectedCallback() {
    if (!this._initialized && this._hass) {
      this._initialized = true;
      this._renderLayout();
      this._fetchData();
      this._checkUpdate();
    }
    // Auto refresh every 60 seconds
    this._refreshInterval = setInterval(() => {
      this._fetchData();
    }, 60000);
  }

  disconnectedCallback() {
    if (this._refreshInterval) {
      clearInterval(this._refreshInterval);
    }
  }

  async _fetchData() {
    if (!this._hass) return;
    try {
      const resp = await this._hass.callApi("GET", "domolink_transport/data");
      if (resp) {
        if (resp.version) {
          this._installedVersion = resp.version;
          this._renderUpdateBadge(Boolean(this._updateInfo));
        }
        if (resp.data) {
          this._data = resp.data;
          this._updateDisplay();
        }
      }
    } catch (e) {
      console.warn("DomoLink-Transport fetch error:", e);
      // Fallback: try to reconstruct from entities if API view was not ready
      this._reconstructFromEntities();
    }
  }

  _reconstructFromEntities() {
    if (!this._hass) return;
    const states = this._hass.states;
    const a_to_b = [];
    for (let i = 1; i <= 3; i++) {
      const s = states[`sensor.domolink_transport_a_to_b_${i}`] || states[`sensor.train_traveler_eng_par_next_journey_${i}`];
      if (s && s.state && s.state !== "unavailable" && s.state !== "unknown") {
        a_to_b.push({
          departure_time: s.state,
          departure_time_str: s.state.substring(11, 16),
          platform: s.attributes.platform || s.attributes.voie || "2",
          line: s.attributes.line || "H",
          direction: s.attributes.direction || "Paris Nord",
          headsign: s.attributes.headsign || s.attributes.mission || "TRAIN",
          status_label: (s.attributes.delay || 0) > 0 ? `Retard +${s.attributes.delay} min` : "À l'heure",
          minutes_remaining: states[`sensor.next_train_minutes_${i}`] ? parseInt(states[`sensor.next_train_minutes_${i}`].state) : 0,
          is_on_time: !(s.attributes.delay > 0),
        });
      }
    }

    const a_to_c = [];
    for (let i = 1; i <= 3; i++) {
      const s = states[`sensor.domolink_transport_a_to_c_${i}`];
      if (s && s.state && s.state !== "unavailable" && s.state !== "unknown") {
        a_to_c.push({
          departure_time: s.state,
          departure_time_str: s.state.substring(11, 16),
          platform: s.attributes.platform || s.attributes.voie || "-",
          line: s.attributes.line || "H",
          direction: s.attributes.direction || "Ermont - Eaubonne",
          headsign: s.attributes.headsign || s.attributes.mission || "TRAIN",
          status_label: (s.attributes.delay || 0) > 0 ? `Retard +${s.attributes.delay} min` : "À l'heure",
          minutes_remaining: s.attributes.minutes_remaining !== undefined ? s.attributes.minutes_remaining : 0,
          is_on_time: !(s.attributes.delay > 0),
        });
      }
    }

    const b_to_a = [];
    for (let i = 1; i <= 3; i++) {
      const s = states[`sensor.domolink_transport_b_to_a_${i}`] || (i === 1 ? states[`sensor.train_traveler_par_eng_next_journey_1`] : null);
      if (s && s.state && s.state !== "unavailable" && s.state !== "unknown") {
        b_to_a.push({
          departure_time: s.state,
          departure_time_str: s.state.substring(11, 16),
          platform: s.attributes.platform || s.attributes.voie || "30-36",
          line: s.attributes.line || "H",
          direction: s.attributes.direction || "Enghien-les-Bains",
          headsign: s.attributes.headsign || s.attributes.mission || "TRAIN",
          status_label: (s.attributes.delay || 0) > 0 ? `Retard +${s.attributes.delay} min` : "À l'heure",
          minutes_remaining: s.attributes.minutes_remaining !== undefined ? s.attributes.minutes_remaining : 0,
          is_on_time: !(s.attributes.delay > 0),
        });
      }
    }

    const c_to_a = [];
    for (let i = 1; i <= 3; i++) {
      const s = states[`sensor.domolink_transport_c_to_a_${i}`];
      if (s && s.state && s.state !== "unavailable" && s.state !== "unknown") {
        c_to_a.push({
          departure_time: s.state,
          departure_time_str: s.state.substring(11, 16),
          platform: s.attributes.platform || s.attributes.voie || "3-4",
          line: s.attributes.line || "H",
          direction: s.attributes.direction || "Enghien-les-Bains",
          headsign: s.attributes.headsign || s.attributes.mission || "TRAIN",
          status_label: (s.attributes.delay || 0) > 0 ? `Retard +${s.attributes.delay} min` : "À l'heure",
          minutes_remaining: s.attributes.minutes_remaining !== undefined ? s.attributes.minutes_remaining : 0,
          is_on_time: !(s.attributes.delay > 0),
        });
      }
    }

    const lastBtoA = states["sensor.domolink_transport_last_return_b_to_a"] || states["sensor.train_traveler_eng_par_last_journey_1"];
    let lastRetB = null;
    if (lastBtoA && lastBtoA.state && lastBtoA.state !== "unavailable") {
      lastRetB = {
        departure_time: lastBtoA.state,
        departure_time_str: lastBtoA.state.substring(11, 16),
        platform: lastBtoA.attributes.platform || lastBtoA.attributes.voie || "30-36",
        line: lastBtoA.attributes.line || "H",
        direction: lastBtoA.attributes.direction || "Enghien-les-Bains",
        headsign: lastBtoA.attributes.headsign || "TRAIN",
        status_label: "À l'heure",
        minutes_remaining: 0,
      };
    }

    const lastCtoA = states["sensor.domolink_transport_last_return_c_to_a"];
    let lastRetC = null;
    if (lastCtoA && lastCtoA.state && lastCtoA.state !== "unavailable") {
      lastRetC = {
        departure_time: lastCtoA.state,
        departure_time_str: lastCtoA.state.substring(11, 16),
        platform: lastCtoA.attributes.platform || lastCtoA.attributes.voie || "3-4",
        line: lastCtoA.attributes.line || "H",
        direction: lastCtoA.attributes.direction || "Enghien-les-Bains",
        headsign: lastCtoA.attributes.headsign || "TRAIN",
        status_label: "À l'heure",
        minutes_remaining: 0,
      };
    }

    this._data = {
      station_a: { name: "Enghien-les-Bains" },
      station_b: { name: "Paris Nord" },
      station_c: { name: "Ermont - Eaubonne" },
      a_to_b: a_to_b,
      a_to_c: a_to_c,
      b_to_a: b_to_a,
      c_to_a: c_to_a,
      last_return_b_to_a: lastRetB,
      last_return_c_to_a: lastRetC,
      disruptions: [],
    };
    this._updateDisplay();
  }

  _parseSemver(v) {
    if (!v) return [0, 0, 0];
    const clean = String(v).replace(/^[vV]/, "").trim();
    const parts = clean.split(".").map(n => parseInt(n, 10) || 0);
    while (parts.length < 3) parts.push(0);
    return parts.slice(0, 3);
  }

  _isNewer(latest, current) {
    const l = this._parseSemver(latest);
    const c = this._parseSemver(current);
    for (let i = 0; i < 3; i++) {
      if (l[i] > c[i]) return true;
      if (l[i] < c[i]) return false;
    }
    return false;
  }

  async _checkUpdate() {
    try {
      const resp = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/releases/latest`);
      if (resp.ok) {
        const data = await resp.json();
        const latestTag = (data.tag_name || "").replace(/^[vV]/, "").trim();
        const currentVer = (this._installedVersion || VERSION).replace(/^[vV]/, "").trim();
        if (latestTag && this._isNewer(latestTag, currentVer)) {
          this._updateInfo = {
            version: latestTag,
            body: data.body || "",
            url: data.html_url,
          };
          this._renderUpdateBadge(true);
        } else {
          this._updateInfo = null;
          this._renderUpdateBadge(false);
        }
      }
    } catch (e) {
      console.debug("Update check skipped", e);
    }
  }

  _renderLayout() {
    if (this._isCard) {
      this.setAttribute("is-card", "true");
    }
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          height: 100vh;
          overflow-y: auto;
          background: #040914;
          color: #e0e6ed;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          box-sizing: border-box;
          container-type: inline-size;
        }

        :host([is-card]), :host(.is-card) {
          height: auto !important;
          max-height: none !important;
          overflow: visible !important;
          background: transparent !important;
        }

        :host([is-card]) .container, :host(.is-card) .container {
          padding: 0 !important;
          margin: 0 !important;
          max-width: 100% !important;
          gap: 14px !important;
        }

        :host([is-card]) .navbar, :host(.is-card) .navbar {
          padding: 8px 12px !important;
          border-radius: 12px !important;
          margin-bottom: 2px !important;
          position: static !important;
          flex-wrap: wrap !important;
          gap: 8px !important;
        }

        :host([is-card]) #btnGenCard, :host(.is-card) #btnGenCard {
          display: none !important;
        }

        :host([is-card]) .brand-title, :host(.is-card) .brand-title {
          font-size: 1.05rem !important;
        }

        :host([is-card]) .destinations-grid, :host(.is-card) .destinations-grid {
          grid-template-columns: 1fr !important;
          gap: 14px !important;
        }

        :host([is-card]) .night-card, :host(.is-card) .night-card {
          grid-template-columns: 1fr !important;
          padding: 12px 14px !important;
          gap: 10px !important;
        }

        :host([is-card]) .board-header, :host(.is-card) .board-header {
          padding: 10px 14px !important;
        }

        :host([is-card]) .board-title, :host(.is-card) .board-title {
          font-size: 1.05rem !important;
        }

        :host([is-card]) .train-table th, :host(.is-card) .train-table th {
          padding: 6px 8px !important;
          font-size: 0.68rem !important;
        }

        :host([is-card]) .train-time, :host(.is-card) .train-time {
          padding: 8px 8px !important;
        }

        :host([is-card]) .train-time-main, :host(.is-card) .train-time-main {
          font-size: 1.25rem !important;
        }

        :host([is-card]) .train-countdown, :host(.is-card) .train-countdown {
          font-size: 0.72rem !important;
          margin-top: 1px !important;
        }

        :host([is-card]) .train-platform, :host(.is-card) .train-platform {
          font-size: 0.95rem !important;
          padding: 3px 6px !important;
          min-width: 28px !important;
        }

        :host([is-card]) .train-dest, :host(.is-card) .train-dest {
          padding: 8px 8px !important;
          font-size: 0.92rem !important;
        }

        :host([is-card]) .train-mission, :host(.is-card) .train-mission {
          padding: 2px 6px !important;
          font-size: 0.76rem !important;
        }

        :host([is-card]) .train-status, :host(.is-card) .train-status {
          padding: 8px 8px !important;
          font-size: 0.8rem !important;
          white-space: nowrap !important;
        }

        :host([is-card]) .return-night-summary, :host(.is-card) .return-night-summary {
          margin: 8px 10px 10px 10px !important;
          padding: 8px 10px !important;
        }

        * {
          box-sizing: border-box;
        }

        /* Top Navbar */
        .navbar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 14px 24px;
          background: #081122;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          position: sticky;
          top: 0;
          z-index: 100;
        }

        .brand {
          display: flex;
          align-items: center;
          gap: 12px;
          cursor: pointer;
          user-select: none;
        }

        .brand-icon {
          width: 36px;
          height: 36px;
          border-radius: 8px;
          background: linear-gradient(135deg, #0077ff, #00d4ff);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 20px;
          box-shadow: 0 4px 12px rgba(0, 119, 255, 0.4);
        }

        .brand-title {
          font-size: 1.25rem;
          font-weight: 700;
          letter-spacing: 0.5px;
          background: linear-gradient(90deg, #ffffff, #a0c4ff);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .brand-badge {
          font-size: 0.75rem;
          background: rgba(0, 119, 255, 0.2);
          color: #00d4ff;
          padding: 2px 8px;
          border-radius: 12px;
          border: 1px solid rgba(0, 212, 255, 0.4);
          font-weight: 600;
        }

        .actions {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .style-switch {
          display: flex;
          background: rgba(255, 255, 255, 0.06);
          border-radius: 20px;
          padding: 3px;
          border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .style-btn {
          padding: 6px 14px;
          border-radius: 16px;
          border: none;
          background: transparent;
          color: #8899a6;
          font-size: 0.85rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .style-btn.active {
          background: #0077ff;
          color: #ffffff;
          box-shadow: 0 2px 8px rgba(0, 119, 255, 0.4);
        }

        .btn-action {
          padding: 7px 14px;
          border-radius: 8px;
          border: 1px solid rgba(255, 255, 255, 0.12);
          background: rgba(255, 255, 255, 0.05);
          color: #e0e6ed;
          font-size: 0.85rem;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 6px;
          transition: all 0.2s;
        }

        .btn-action:hover {
          background: rgba(255, 255, 255, 0.12);
          border-color: rgba(255, 255, 255, 0.25);
        }

        .btn-update {
          background: linear-gradient(135deg, #ff3366, #ff6b3d);
          color: #fff;
          border: none;
          animation: pulse 2s infinite;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.9; transform: scale(1.03); }
        }

        /* Container */
        .container {
          max-width: 1400px;
          margin: 0 auto;
          padding: 24px;
          display: flex;
          flex-direction: column;
          gap: 24px;
        }

        /* BOARD CONTAINER */
        .board-card {
          border-radius: 16px;
          overflow: hidden;
          transition: all 0.3s ease;
        }

        /* ---------------- MODERN INFOGARE STYLE ---------------- */
        .modern-theme .board-card {
          background: #061325;
          border: 2px solid #0a254c;
          box-shadow: 0 12px 36px rgba(0, 0, 0, 0.6), 0 0 20px rgba(0, 119, 255, 0.15);
        }

        .modern-theme .board-header {
          background: #030b18;
          padding: 16px 24px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          border-bottom: 2px solid #0055ff;
        }

        .modern-theme .board-title {
          font-size: 1.35rem;
          font-weight: 800;
          letter-spacing: 1.5px;
          color: #ffde59;
          text-transform: uppercase;
          display: flex;
          align-items: center;
          gap: 12px;
          text-shadow: 0 0 12px rgba(255, 222, 89, 0.4);
        }

        .modern-theme .train-table {
          width: 100%;
          border-collapse: collapse;
        }

        .modern-theme .train-table th {
          background: #091a33;
          color: #7b9acc;
          text-transform: uppercase;
          font-size: 0.72rem;
          letter-spacing: 1px;
          padding: 8px 10px;
          text-align: left;
          font-weight: 700;
        }

        .modern-theme .train-row {
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
          transition: background 0.2s;
        }

        .modern-theme .train-row:hover {
          background: rgba(0, 119, 255, 0.08);
        }

        .modern-theme .train-time {
          padding: 8px 10px;
        }

        .modern-theme .train-time-main {
          font-size: 1.5rem;
          font-weight: 900;
          color: #ffde59;
          line-height: 1.1;
          font-variant-numeric: tabular-nums;
          letter-spacing: 1px;
          text-shadow: 0 0 8px rgba(255, 222, 89, 0.3);
        }

        .modern-theme .train-dest {
          font-size: 1.05rem;
          font-weight: 700;
          color: #ffffff;
          padding: 8px 10px;
        }

        .modern-theme .train-mission {
          display: inline-block;
          background: #002b66;
          color: #38b6ff;
          padding: 3px 8px;
          border-radius: 6px;
          font-weight: 800;
          font-size: 0.85rem;
          letter-spacing: 1px;
          border: 1px solid #0055ff;
        }

        .modern-theme .train-platform {
          font-size: 1.25rem;
          font-weight: 900;
          color: #030b18;
          background: #ffde59;
          padding: 3px 8px;
          border-radius: 8px;
          display: inline-block;
          text-align: center;
          min-width: 32px;
          box-shadow: 0 0 10px rgba(255, 222, 89, 0.5);
        }

        .modern-theme .train-platform.platform-range {
          font-size: 0.95rem;
          padding: 2px 6px;
          letter-spacing: -0.5px;
          min-width: 28px;
        }

        .mechanical-theme .flap-box.platform-range {
          font-size: 1rem !important;
          letter-spacing: 0px !important;
          padding: 4px 6px !important;
        }

        .modern-theme .train-status {
          font-size: 0.92rem;
          font-weight: 700;
          padding: 8px 10px;
          text-align: right;
          white-space: nowrap;
        }

        .status-ontime {
          color: #00ff88;
          text-shadow: 0 0 8px rgba(0, 255, 136, 0.4);
        }

        .status-delayed {
          color: #ff3344;
          text-shadow: 0 0 8px rgba(255, 51, 68, 0.5);
          animation: blink 1s infinite alternate;
        }

        .status-approaching {
          color: #ff9900;
          text-shadow: 0 0 8px rgba(255, 153, 0, 0.4);
        }

        @keyframes blink {
          from { opacity: 1; }
          to { opacity: 0.5; }
        }

        .modern-theme .train-countdown {
          font-size: 0.95rem;
          font-weight: 700;
          color: #7ba6e8;
          margin-top: 4px;
        }

        /* ---------------- MECHANICAL SPLIT-FLAP STYLE ---------------- */
        .mechanical-theme .board-card {
          background: #111114;
          border: 4px solid #28282e;
          box-shadow: inset 0 0 30px rgba(0, 0, 0, 0.9), 0 16px 40px rgba(0, 0, 0, 0.8);
        }

        .mechanical-theme .board-header {
          background: #0a0a0c;
          padding: 16px 24px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          border-bottom: 2px solid #333339;
        }

        .mechanical-theme .board-title {
          font-family: 'Courier New', Courier, monospace;
          font-size: 1.4rem;
          font-weight: 900;
          letter-spacing: 3px;
          color: #d1d1d6;
          text-transform: uppercase;
        }

        .mechanical-theme .train-table {
          width: 100%;
          border-collapse: separate;
          border-spacing: 0 8px;
          padding: 8px 16px;
        }

        .mechanical-theme .train-table th {
          font-family: 'Courier New', monospace;
          color: #666670;
          text-transform: uppercase;
          font-size: 0.75rem;
          letter-spacing: 2px;
          padding: 8px 12px;
          text-align: left;
        }

        .mechanical-theme .train-row {
          background: #19191d;
          box-shadow: 0 4px 8px rgba(0,0,0,0.5);
        }

        .mechanical-theme .flap-box {
          display: inline-block;
          background: #0c0c0e;
          color: #f0f0f5;
          font-family: 'Courier New', monospace;
          font-weight: 900;
          padding: 6px 10px;
          border-radius: 4px;
          border: 1px solid #33333a;
          box-shadow: inset 0 -4px 0 #18181c, 0 2px 4px rgba(0,0,0,0.6);
          position: relative;
          letter-spacing: 2px;
        }

        .mechanical-theme .flap-box::after {
          content: "";
          position: absolute;
          left: 0;
          top: 50%;
          width: 100%;
          height: 1px;
          background: rgba(0, 0, 0, 0.85);
          box-shadow: 0 1px 0 rgba(255, 255, 255, 0.1);
        }

        .mechanical-theme .train-time .flap-box {
          font-size: 1.4rem;
          color: #ffcc00;
        }

        .mechanical-theme .train-platform .flap-box {
          font-size: 1.3rem;
          color: #ff3344;
        }

        .mechanical-theme .train-dest {
          font-family: 'Courier New', monospace;
          font-size: 1.15rem;
          font-weight: 800;
          color: #e5e5ea;
          letter-spacing: 1px;
        }

        /* Section Headers */
        .section-header {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          margin-bottom: 14px;
          padding-bottom: 8px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }

        .section-title {
          font-size: 1.2rem;
          font-weight: 800;
          letter-spacing: 0.5px;
          color: #e0e6ed;
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .section-subtitle {
          font-size: 0.85rem;
          color: #718096;
          font-weight: 600;
        }

        /* Return Night Summary inside cards */
        .return-night-summary {
          margin: 14px 18px 18px 18px;
          padding: 12px 16px;
          border-radius: 12px;
          background: linear-gradient(135deg, rgba(0, 40, 100, 0.45) 0%, rgba(0, 80, 160, 0.25) 100%);
          border: 1px solid rgba(0, 170, 255, 0.3);
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 10px;
        }

        .night-badge {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          font-size: 0.75rem;
          font-weight: 800;
          letter-spacing: 0.5px;
          text-transform: uppercase;
          color: #ffde59;
          background: rgba(255, 222, 89, 0.15);
          border: 1px solid rgba(255, 222, 89, 0.35);
          padding: 4px 10px;
          border-radius: 6px;
          white-space: nowrap;
        }

        .night-info {
          display: flex;
          align-items: center;
          gap: 12px;
          flex-wrap: wrap;
        }

        .night-dep {
          font-size: 1.4rem;
          font-weight: 900;
          color: #ffde59;
          font-variant-numeric: tabular-nums;
        }

        .night-platform {
          font-size: 0.9rem;
          font-weight: 800;
          color: #00d4ff;
          background: rgba(0, 212, 255, 0.15);
          padding: 3px 8px;
          border-radius: 6px;
          border: 1px solid rgba(0, 212, 255, 0.3);
          white-space: nowrap;
        }

        .night-desc {
          font-size: 0.85rem;
          color: #a0aec0;
          font-weight: 500;
        }

        .mechanical-theme .return-night-summary {
          background: #101014;
          border: 1px solid #282830;
          box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.7);
        }

        .mechanical-theme .night-badge {
          font-family: 'Courier New', monospace;
          background: #0a0a0c;
          border: 1px solid #33333a;
          color: #ffcc00;
        }

        .mechanical-theme .night-dep {
          font-family: 'Courier New', monospace;
          color: #ffcc00;
        }

        .mechanical-theme .night-platform {
          font-family: 'Courier New', monospace;
          color: #ff3344;
          background: #0a0a0c;
          border: 1px solid #33333a;
        }

        .mechanical-theme .night-desc {
          font-family: 'Courier New', monospace;
          color: #a0aec0;
        }

        /* Grid for 2 destinations */
        .destinations-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
          gap: 16px;
        }

        /* Night returns panel */
        .night-card {
          border-radius: 16px;
          background: linear-gradient(135deg, #091326 0%, #111a33 100%);
          border: 1px solid rgba(0, 150, 255, 0.25);
          padding: 20px 24px;
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
          gap: 20px;
        }

        .night-title {
          grid-column: 1 / -1;
          font-size: 1.15rem;
          font-weight: 800;
          color: #00d4ff;
          display: flex;
          align-items: center;
          gap: 10px;
          letter-spacing: 0.5px;
          text-transform: uppercase;
        }

        .night-return-box {
          background: rgba(0, 0, 0, 0.3);
          border-radius: 12px;
          padding: 16px 20px;
          border: 1px solid rgba(255, 255, 255, 0.08);
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .night-route {
          font-size: 1.05rem;
          font-weight: 700;
          color: #fff;
          margin-bottom: 4px;
        }

        .night-details {
          font-size: 0.85rem;
          color: #8899a6;
        }

        .night-time {
          font-size: 1.5rem;
          font-weight: 900;
          color: #ffde59;
          text-align: right;
        }

        /* Traffic Ticker */
        .ticker-bar {
          background: #020712;
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 12px;
          padding: 12px 20px;
          display: flex;
          align-items: center;
          gap: 16px;
          overflow: hidden;
        }

        .ticker-badge {
          background: #00ff88;
          color: #040914;
          font-size: 0.75rem;
          font-weight: 800;
          padding: 4px 10px;
          border-radius: 6px;
          text-transform: uppercase;
          white-space: nowrap;
        }

        .ticker-badge.disrupted {
          background: #ff3344;
          color: #ffffff;
        }

        .ticker-content {
          font-size: 0.9rem;
          color: #c0d0e6;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        /* Modal */
        .modal-overlay {
          position: fixed;
          top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0, 0, 0, 0.8);
          backdrop-filter: blur(6px);
          display: none;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }

        .modal-overlay.open {
          display: flex;
        }

        .modal-card {
          background: #0b172a;
          border: 1px solid rgba(255, 255, 255, 0.15);
          border-radius: 16px;
          max-width: 650px;
          width: 90%;
          padding: 24px;
          box-shadow: 0 20px 50px rgba(0,0,0,0.8);
        }

        .modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }

        .modal-title {
          font-size: 1.25rem;
          font-weight: 700;
          color: #fff;
        }

        .modal-close {
          background: transparent;
          border: none;
          color: #8899a6;
          font-size: 1.5rem;
          cursor: pointer;
        }

        .code-box {
          background: #040a14;
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 8px;
          padding: 16px;
          font-family: monospace;
          font-size: 0.85rem;
          color: #00ff88;
          max-height: 250px;
          overflow-y: auto;
          white-space: pre-wrap;
          margin-bottom: 16px;
        }

        @media (max-width: 820px) {
          .destinations-grid {
            grid-template-columns: 1fr;
          }
          .container {
            padding: 12px;
            gap: 14px;
          }
          .navbar {
            padding: 10px 14px;
            gap: 8px;
            flex-wrap: wrap;
          }
        }

        @container (max-width: 540px) {
          .destinations-grid {
            grid-template-columns: 1fr !important;
            gap: 12px !important;
          }
          .board-header {
            padding: 8px 10px !important;
          }
          .board-title {
            font-size: 0.95rem !important;
          }
          .modern-theme .train-table th {
            padding: 5px 6px !important;
            font-size: 0.65rem !important;
          }
          .modern-theme .train-time {
            padding: 6px 6px !important;
          }
          .modern-theme .train-time-main {
            font-size: 1.15rem !important;
          }
          .modern-theme .train-countdown {
            font-size: 0.68rem !important;
          }
          .modern-theme .train-platform {
            font-size: 0.85rem !important;
            padding: 2px 5px !important;
            min-width: 24px !important;
          }
          .modern-theme .train-dest {
            padding: 6px 6px !important;
            font-size: 0.85rem !important;
          }
          .modern-theme .train-mission {
            font-size: 0.72rem !important;
            padding: 1px 4px !important;
          }
          .modern-theme .train-status {
            padding: 6px 6px !important;
            font-size: 0.75rem !important;
          }
          .night-card {
            grid-template-columns: 1fr !important;
            padding: 10px 12px !important;
          }
        }
      </style>

      <div class="${this._styleMode}-theme" id="themeWrapper">
        <!-- TOP NAVBAR -->
        <div class="navbar">
          <div class="brand" id="brandLogo">
            <div class="brand-icon">🚆</div>
            <div>
              <div class="brand-title">DomoLink-Transport</div>
            </div>
            <div class="brand-badge" id="versionBadge">v${VERSION}</div>
          </div>

          <div class="actions">
            <!-- STYLE SWITCH -->
            <div class="style-switch">
              <button class="style-btn ${this._styleMode === 'modern' ? 'active' : ''}" id="btnStyleModern">
                🚆 Moderne
              </button>
              <button class="style-btn ${this._styleMode === 'mechanical' ? 'active' : ''}" id="btnStyleMech">
                📟 Mécanique
              </button>
            </div>

            <button class="btn-action" id="btnGenCard">
              📋 Carte Lovelace
            </button>

            <button class="btn-action" id="btnRefresh">
              🔄 Actualiser
            </button>

            <button class="btn-action btn-update" id="btnUpdate" style="display: none;">
              ⬆️ Mettre à jour
            </button>
          </div>
        </div>

        <!-- MAIN CONTAINER -->
        <div class="container">
          <!-- FLASH INFO TRAFIC TICKER -->
          <div class="ticker-bar">
            <div class="ticker-badge" id="tickerBadge">Ligne H • Trafic Normal</div>
            <div class="ticker-content" id="tickerContent">Circulation normale sur l'ensemble de la Ligne H.</div>
          </div>

          <!-- SECTION DÉPARTS -->
          <div class="section-header">
            <div class="section-title">
              <span>🚆 DÉPARTS DEPUIS <span id="sectionDepTitle">ENGHIEN</span></span>
            </div>
            <div class="section-subtitle">3 prochains trains vers vos destinations</div>
          </div>

          <div class="destinations-grid">
            <!-- TABLEAU A -> B -->
            <div class="board-card">
              <div class="board-header">
                <div class="board-title" id="titleAtoB">
                  🚆 <span id="labelStationA">ENGHIEN</span> ➔ <span id="labelStationB">PARIS NORD</span>
                </div>
                <div style="font-size: 0.85rem; color: #8899a6; font-weight: 600;">3 PROCHAINS DÉPARTS</div>
              </div>
              <table class="train-table">
                <thead>
                  <tr>
                    <th>Départ</th>
                    <th>Voie</th>
                    <th>Mission / Direction</th>
                    <th style="text-align: right;">Statut</th>
                  </tr>
                </thead>
                <tbody id="tbodyAtoB">
                  <tr><td colspan="4" style="text-align: center; padding: 24px; color: #8899a6;">Chargement des prochains trains...</td></tr>
                </tbody>
              </table>
            </div>

            <!-- TABLEAU A -> C -->
            <div class="board-card">
              <div class="board-header">
                <div class="board-title" id="titleAtoC">
                  🚆 <span id="labelStationA2">ENGHIEN</span> ➔ <span id="labelStationC">ERMONT - EAUBONNE</span>
                </div>
                <div style="font-size: 0.85rem; color: #8899a6; font-weight: 600;">3 PROCHAINS DÉPARTS</div>
              </div>
              <table class="train-table">
                <thead>
                  <tr>
                    <th>Départ</th>
                    <th>Voie</th>
                    <th>Mission / Direction</th>
                    <th style="text-align: right;">Statut</th>
                  </tr>
                </thead>
                <tbody id="tbodyAtoC">
                  <tr><td colspan="4" style="text-align: center; padding: 24px; color: #8899a6;">Chargement des prochains trains...</td></tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- SECTION RETOURS -->
          <div class="section-header" style="margin-top: 32px;">
            <div class="section-title">
              <span>🔄 RETOURS VERS <span id="sectionRetTitle">ENGHIEN</span></span>
            </div>
            <div class="section-subtitle">3 prochains retours & Dernier train avant coupure</div>
          </div>

          <div class="destinations-grid">
            <!-- TABLEAU B -> A -->
            <div class="board-card">
              <div class="board-header">
                <div class="board-title" id="titleBtoA">
                  🚆 <span id="labelStationB_ret">PARIS NORD</span> ➔ <span id="labelStationA_ret">ENGHIEN</span>
                </div>
                <div style="font-size: 0.85rem; color: #8899a6; font-weight: 600;">3 PROCHAINS RETOURS</div>
              </div>
              <table class="train-table">
                <thead>
                  <tr>
                    <th>Départ</th>
                    <th>Voie</th>
                    <th>Mission / Direction</th>
                    <th style="text-align: right;">Statut</th>
                  </tr>
                </thead>
                <tbody id="tbodyBtoA">
                  <tr><td colspan="4" style="text-align: center; padding: 24px; color: #8899a6;">Chargement des retours...</td></tr>
                </tbody>
              </table>
              <!-- DERNIER RETOUR EN BAS DE CARTE -->
              <div class="return-night-summary">
                <div class="night-badge">🌙 DERNIER RETOUR</div>
                <div class="night-info">
                  <span class="night-dep" id="cardNightTimeBtoA">--:--</span>
                  <span class="night-platform" id="cardNightPlatBtoA">Voie --</span>
                  <span class="night-desc" id="cardNightDescBtoA">Dernier train avant coupure</span>
                </div>
              </div>
            </div>

            <!-- TABLEAU C -> A -->
            <div class="board-card">
              <div class="board-header">
                <div class="board-title" id="titleCtoA">
                  🚆 <span id="labelStationC_ret">ERMONT - EAUBONNE</span> ➔ <span id="labelStationA_ret2">ENGHIEN</span>
                </div>
                <div style="font-size: 0.85rem; color: #8899a6; font-weight: 600;">3 PROCHAINS RETOURS</div>
              </div>
              <table class="train-table">
                <thead>
                  <tr>
                    <th>Départ</th>
                    <th>Voie</th>
                    <th>Mission / Direction</th>
                    <th style="text-align: right;">Statut</th>
                  </tr>
                </thead>
                <tbody id="tbodyCtoA">
                  <tr><td colspan="4" style="text-align: center; padding: 24px; color: #8899a6;">Chargement des retours...</td></tr>
                </tbody>
              </table>
              <!-- DERNIER RETOUR EN BAS DE CARTE -->
              <div class="return-night-summary">
                <div class="night-badge">🌙 DERNIER RETOUR</div>
                <div class="night-info">
                  <span class="night-dep" id="cardNightTimeCtoA">--:--</span>
                  <span class="night-platform" id="cardNightPlatCtoA">Voie --</span>
                  <span class="night-desc" id="cardNightDescCtoA">Dernier train avant coupure</span>
                </div>
              </div>
            </div>
          </div>

          <!-- DERNIERS RETOURS DE NUIT (RÉSUMÉ) -->
          <div class="night-card" style="margin-top: 24px;">
            <div class="night-title">
              🌙 Synthèse Coupure Nocturne
            </div>

            <!-- RETOUR B -> A -->
            <div class="night-return-box">
              <div>
                <div class="night-route" id="nightRouteBtoA">PARIS NORD ➔ ENGHIEN</div>
                <div class="night-details" id="nightDetailsBtoA">Dernier train pour rentrer de Paris</div>
              </div>
              <div style="text-align: right;">
                <div class="night-time" id="nightTimeBtoA">--:--</div>
                <div style="font-size: 0.85rem; color: #00d4ff; font-weight: 700;" id="nightPlatformBtoA">Voie --</div>
              </div>
            </div>

            <!-- RETOUR C -> A -->
            <div class="night-return-box">
              <div>
                <div class="night-route" id="nightRouteCtoA">ERMONT ➔ ENGHIEN</div>
                <div class="night-details" id="nightDetailsCtoA">Dernier train pour rentrer d'Ermont</div>
              </div>
              <div style="text-align: right;">
                <div class="night-time" id="nightTimeCtoA">--:--</div>
                <div style="font-size: 0.85rem; color: #00d4ff; font-weight: 700;" id="nightPlatformCtoA">Voie --</div>
              </div>
            </div>
          </div>
        </div>

        <!-- MODALE LOVELACE CARD GENERATOR -->
        <div class="modal-overlay" id="modalCard">
          <div class="modal-card">
            <div class="modal-header">
              <div class="modal-title">📋 Carte Lovelace DomoLink-Transport</div>
              <button class="modal-close" id="btnCloseModal">&times;</button>
            </div>
            <p style="color: #a0aec0; font-size: 0.9rem; margin-bottom: 12px;">
              Vous pouvez ajouter ce panneau directement dans n'importe quel tableau de bord Home Assistant Lovelace avec le code suivant :
            </p>
            <div class="code-box" id="cardYamlCode">type: custom:domolink-transport-card
style: ${this._styleMode}
station_a: Enghien-les-Bains
station_b: Paris Nord
station_c: Ermont - Eaubonne</div>
            <button class="btn-action" id="btnCopyYaml" style="width: 100%; justify-content: center; background: #0077ff; color: #fff;">
              Copier le code YAML
            </button>
          </div>
        </div>

        <!-- MODALE UPDATE -->
        <div class="modal-overlay" id="modalUpdate">
          <div class="modal-card">
            <div class="modal-header">
              <div class="modal-title">⬆️ Mise à jour disponible</div>
              <button class="modal-close" id="btnCloseUpdate">&times;</button>
            </div>
            <p id="updateBodyText" style="color: #a0aec0; font-size: 0.9rem; margin-bottom: 16px;"></p>
            <button class="btn-action btn-update" id="btnInstallUpdate" style="width: 100%; justify-content: center;">
              Installer la mise à jour maintenant & Redémarrer
            </button>
          </div>
        </div>
      </div>
    `;

    this._bindEvents();
  }

  _bindEvents() {
    const root = this.shadowRoot;

    // Style toggle
    root.getElementById("btnStyleModern").addEventListener("click", () => {
      this._setStyle("modern");
    });
    root.getElementById("btnStyleMech").addEventListener("click", () => {
      this._setStyle("mechanical");
    });

    // Refresh
    root.getElementById("btnRefresh").addEventListener("click", async () => {
      const btn = root.getElementById("btnRefresh");
      btn.innerHTML = "⏳ Actualisation...";
      try {
        await this._hass.callApi("POST", "domolink_transport/refresh");
        setTimeout(() => this._fetchData(), 1200);
      } catch (e) {
        this._fetchData();
      }
      setTimeout(() => { btn.innerHTML = "🔄 Actualiser"; }, 1500);
    });

    // Lovelace generator
    root.getElementById("btnGenCard").addEventListener("click", () => {
      root.getElementById("modalCard").classList.add("open");
    });
    root.getElementById("btnCloseModal").addEventListener("click", () => {
      root.getElementById("modalCard").classList.remove("open");
    });
    root.getElementById("btnCopyYaml").addEventListener("click", () => {
      const code = root.getElementById("cardYamlCode").innerText;
      navigator.clipboard.writeText(code);
      const btn = root.getElementById("btnCopyYaml");
      btn.innerText = "✅ Code copié dans le presse-papier !";
      setTimeout(() => { btn.innerText = "Copier le code YAML"; }, 2500);
    });

    // Update modal
    root.getElementById("btnUpdate").addEventListener("click", () => {
      root.getElementById("modalUpdate").classList.add("open");
    });
    root.getElementById("btnCloseUpdate").addEventListener("click", () => {
      root.getElementById("modalUpdate").classList.remove("open");
    });
    root.getElementById("btnInstallUpdate").addEventListener("click", async () => {
      const btn = root.getElementById("btnInstallUpdate");
      btn.innerText = "⏳ Installation en cours...";
      try {
        // Priorité à l'entité native domolink_transport_systeme puis domolink_transport
        const updateEntities = Object.keys(this._hass.states).filter(eid =>
          eid.startsWith("update.domolink_transport")
        );
        const targetEntity = updateEntities.find(e => e.includes("systeme")) || updateEntities[0] || "update.domolink_transport_systeme_mise_a_jour_domolink_transport";
        const stateObj = this._hass.states[targetEntity];
        if (stateObj && stateObj.state === "off" && stateObj.attributes.installed_version === stateObj.attributes.latest_version) {
          btn.innerText = "✅ Déjà à jour !";
          setTimeout(() => {
            root.getElementById("modalUpdate").classList.remove("open");
            this._renderUpdateBadge(false);
          }, 1000);
          return;
        }
        await this._hass.callService("update", "install", {
          entity_id: targetEntity,
        });
      } catch (e) {
        console.warn("Erreur install update:", e);
        btn.innerText = "⚠️ Échec de l'installation";
        setTimeout(() => {
          btn.innerText = "Installer la mise à jour maintenant & Redémarrer";
        }, 3000);
      }
    });

    // Easter Egg trigger: triple click on logo
    const brand = root.getElementById("brandLogo");
    brand.addEventListener("click", () => {
      this._logoClickCount++;
      clearTimeout(this._logoClickTimer);
      if (this._logoClickCount >= 3) {
        this._logoClickCount = 0;
        launchSocrateRulesEasterEgg(this.shadowRoot);
      } else {
        this._logoClickTimer = setTimeout(() => {
          this._logoClickCount = 0;
        }, 1200);
      }
    });
  }

  _setStyle(mode) {
    this._styleMode = mode;
    localStorage.setItem("domolink_transport_style", mode);
    const wrapper = this.shadowRoot.getElementById("themeWrapper");
    wrapper.className = `${mode}-theme`;
    this.shadowRoot.getElementById("btnStyleModern").classList.toggle("active", mode === "modern");
    this.shadowRoot.getElementById("btnStyleMech").classList.toggle("active", mode === "mechanical");
    this._updateDisplay();
  }

  _renderUpdateBadge(hasUpdate = false) {
    const currentVer = (this._installedVersion || VERSION).replace(/^[vV]/, "").trim();
    const badge = this.shadowRoot.getElementById("versionBadge");
    const btnUp = this.shadowRoot.getElementById("btnUpdate");
    if (!badge) return;

    if (hasUpdate && this._updateInfo) {
      badge.innerText = `v${currentVer} ➔ v${this._updateInfo.version} 🔴`;
      badge.style.background = "rgba(255, 51, 68, 0.25)";
      badge.style.borderColor = "#ff3344";
      badge.style.color = "#ff3344";

      if (btnUp) {
        btnUp.style.display = "flex";
        btnUp.innerText = `⬆️ Maj v${this._updateInfo.version}`;
      }

      const upText = this.shadowRoot.getElementById("updateBodyText");
      if (upText) {
        upText.innerText = this._updateInfo.body || `Une nouvelle version (${this._updateInfo.version}) est disponible.`;
      }
    } else {
      badge.innerText = `v${currentVer}`;
      badge.style.background = "rgba(79, 140, 255, 0.15)";
      badge.style.borderColor = "rgba(79, 140, 255, 0.3)";
      badge.style.color = "#7ba6e8";

      if (btnUp) {
        btnUp.style.display = "none";
      }
    }
  }

  _updateDisplay() {
    if (!this._data) return;
    const root = this.shadowRoot;
    const data = this._data;

    // Station names
    const stA = (data.station_a && data.station_a.name) || "Enghien-les-Bains";
    const stB = (data.station_b && data.station_b.name) || "Paris Nord";
    const stC = (data.station_c && data.station_c.name) || "Ermont - Eaubonne";

    // Section Titles
    if (root.getElementById("sectionDepTitle")) root.getElementById("sectionDepTitle").innerText = stA.toUpperCase();
    if (root.getElementById("sectionRetTitle")) root.getElementById("sectionRetTitle").innerText = stA.toUpperCase();

    // Station labels - Départs
    root.getElementById("labelStationA").innerText = stA.toUpperCase();
    root.getElementById("labelStationB").innerText = stB.toUpperCase();
    root.getElementById("labelStationA2").innerText = stA.toUpperCase();
    root.getElementById("labelStationC").innerText = stC.toUpperCase();

    // Station labels - Retours
    if (root.getElementById("labelStationB_ret")) root.getElementById("labelStationB_ret").innerText = stB.toUpperCase();
    if (root.getElementById("labelStationA_ret")) root.getElementById("labelStationA_ret").innerText = stA.toUpperCase();
    if (root.getElementById("labelStationC_ret")) root.getElementById("labelStationC_ret").innerText = stC.toUpperCase();
    if (root.getElementById("labelStationA_ret2")) root.getElementById("labelStationA_ret2").innerText = stA.toUpperCase();

    // Render Table A -> B (Départs vers B)
    this._renderTableRows(root.getElementById("tbodyAtoB"), data.a_to_b || [], stB);

    // Render Table A -> C (Départs vers C)
    this._renderTableRows(root.getElementById("tbodyAtoC"), data.a_to_c || [], stC);

    // Render Table B -> A (3 prochains retours de Paris vers Enghien)
    this._renderTableRows(root.getElementById("tbodyBtoA"), data.b_to_a || [], stA);

    // Render Table C -> A (3 prochains retours d'Ermont vers Enghien)
    this._renderTableRows(root.getElementById("tbodyCtoA"), data.c_to_a || [], stA);

    // Render Night Returns
    const retB = data.last_return_b_to_a;
    root.getElementById("nightRouteBtoA").innerText = `${stB.toUpperCase()} ➔ ${stA.toUpperCase()}`;
    if (retB && retB.departure_time_str) {
      const arrStr = retB.arrival_time_str ? ` • Arrivée à ${stA} à ${retB.arrival_time_str}` : '';
      let countdownPart = '';
      if (retB.minutes_remaining !== undefined) {
        if (retB.minutes_remaining > 60) {
          countdownPart = `(dans ${Math.floor(retB.minutes_remaining / 60)}h${String(retB.minutes_remaining % 60).padStart(2, '0')})`;
        } else if (retB.minutes_remaining > 0) {
          countdownPart = `(dans ${retB.minutes_remaining} min)`;
        } else {
          countdownPart = `(déjà parti)`;
        }
      }
      root.getElementById("nightTimeBtoA").innerText = retB.departure_time_str;
      root.getElementById("nightPlatformBtoA").innerText = `Voie ${retB.platform || '-'}`;
      root.getElementById("nightDetailsBtoA").innerText = `Dernier train ce soir avant coupure • Ligne ${retB.line || 'H'} (${retB.headsign || 'Mission'})${arrStr} ${countdownPart}`;

      if (root.getElementById("cardNightTimeBtoA")) root.getElementById("cardNightTimeBtoA").innerText = retB.departure_time_str;
      if (root.getElementById("cardNightPlatBtoA")) root.getElementById("cardNightPlatBtoA").innerText = `Voie ${retB.platform || '-'}`;
      if (root.getElementById("cardNightDescBtoA")) root.getElementById("cardNightDescBtoA").innerText = `Ligne ${retB.line || 'H'} (${retB.headsign || 'Mission'})${arrStr} ${countdownPart}`;
    } else {
      root.getElementById("nightTimeBtoA").innerText = "Terminé";
      root.getElementById("nightPlatformBtoA").innerText = "-";
      root.getElementById("nightDetailsBtoA").innerText = "Coupure nocturne en cours (service terminé pour cette nuit)";

      if (root.getElementById("cardNightTimeBtoA")) root.getElementById("cardNightTimeBtoA").innerText = "Terminé";
      if (root.getElementById("cardNightPlatBtoA")) root.getElementById("cardNightPlatBtoA").innerText = "-";
      if (root.getElementById("cardNightDescBtoA")) root.getElementById("cardNightDescBtoA").innerText = "Coupure nocturne en cours";
    }

    const retC = data.last_return_c_to_a;
    root.getElementById("nightRouteCtoA").innerText = `${stC.toUpperCase()} ➔ ${stA.toUpperCase()}`;
    if (retC && retC.departure_time_str) {
      const arrStr = retC.arrival_time_str ? ` • Arrivée à ${stA} à ${retC.arrival_time_str}` : '';
      let countdownPart = '';
      if (retC.minutes_remaining !== undefined) {
        if (retC.minutes_remaining > 60) {
          countdownPart = `(dans ${Math.floor(retC.minutes_remaining / 60)}h${String(retC.minutes_remaining % 60).padStart(2, '0')})`;
        } else if (retC.minutes_remaining > 0) {
          countdownPart = `(dans ${retC.minutes_remaining} min)`;
        } else {
          countdownPart = `(déjà parti)`;
        }
      }
      root.getElementById("nightTimeCtoA").innerText = retC.departure_time_str;
      root.getElementById("nightPlatformCtoA").innerText = `Voie ${retC.platform || '-'}`;
      root.getElementById("nightDetailsCtoA").innerText = `Dernier train ce soir avant coupure • Ligne ${retC.line || 'H'} (${retC.headsign || 'Mission'})${arrStr} ${countdownPart}`;

      if (root.getElementById("cardNightTimeCtoA")) root.getElementById("cardNightTimeCtoA").innerText = retC.departure_time_str;
      if (root.getElementById("cardNightPlatCtoA")) root.getElementById("cardNightPlatCtoA").innerText = `Voie ${retC.platform || '-'}`;
      if (root.getElementById("cardNightDescCtoA")) root.getElementById("cardNightDescCtoA").innerText = `Ligne ${retC.line || 'H'} (${retC.headsign || 'Mission'})${arrStr} ${countdownPart}`;
    } else {
      root.getElementById("nightTimeCtoA").innerText = "Terminé";
      root.getElementById("nightPlatformCtoA").innerText = "-";
      root.getElementById("nightDetailsCtoA").innerText = "Coupure nocturne en cours (service terminé pour cette nuit)";

      if (root.getElementById("cardNightTimeCtoA")) root.getElementById("cardNightTimeCtoA").innerText = "Terminé";
      if (root.getElementById("cardNightPlatCtoA")) root.getElementById("cardNightPlatCtoA").innerText = "-";
      if (root.getElementById("cardNightDescCtoA")) root.getElementById("cardNightDescCtoA").innerText = "Coupure nocturne en cours";
    }

    // Ticker disruptions & quota
    const disruptions = data.disruptions || [];
    const tickerBadge = root.getElementById("tickerBadge");
    const tickerContent = root.getElementById("tickerContent");

    if (data.quota_reached) {
      tickerBadge.className = "ticker-badge disrupted";
      tickerBadge.innerText = "Quota SNCF 5000/j";
      tickerContent.innerText = "Quota journalier atteint (5000 requêtes). Données en cache affichées. Réinitialisation cette nuit (ou changez la clé dans les Options).";
    } else if (disruptions.length > 0) {
      tickerBadge.className = "ticker-badge disrupted";
      tickerBadge.innerText = `Ligne H • ${disruptions.length} Perturbation(s)`;
      tickerContent.innerText = disruptions.map(d => d.message).join(" | ");
    } else {
      tickerBadge.className = "ticker-badge";
      tickerBadge.innerText = "Ligne H • Trafic Normal";
      tickerContent.innerText = "Circulation normale sur l'ensemble de la Ligne H.";
    }
  }

  _renderTableRows(tbody, journeys, destinationDefault) {
    if (!journeys || journeys.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 24px; color: #8899a6;">Aucun train annoncé prochainement.</td></tr>`;
      return;
    }

    const isMech = this._styleMode === "mechanical";
    let html = "";

    journeys.slice(0, 3).forEach((j) => {
      const time = j.departure_time_str || "--:--";
      const platform = j.platform || "-";
      const mission = j.headsign || "TRAIN";
      const dest = j.direction || destinationDefault;
      const mins = j.minutes_remaining;
      const delay = j.delay_minutes || 0;

      let statusClass = "status-ontime";
      let statusText = "À l'heure";

      if (delay > 0) {
        statusClass = "status-delayed";
        statusText = `Retard +${delay} min`;
      } else if (mins <= 2) {
        statusClass = "status-approaching";
        statusText = "À quai";
      }

      const countdownText = mins !== undefined ? (mins > 0 ? `dans ${mins} min` : "départ") : "";

      const platformRangeClass = (platform && platform.length > 2) ? "platform-range" : "";
      const platformTitle = platform === "30-36" ? "Surface (Voies 30 à 36)" : (platform === "3-4" ? "Voies 3 ou 4" : `Voie ${platform}`);

      if (isMech) {
        html += `
          <tr class="train-row">
            <td class="train-time" style="padding: 8px 10px;">
              <div><span class="flap-box">${time}</span></div>
              <div style="font-family: monospace; font-size: 0.75rem; color: #a0aec0; margin-top: 3px;">(${countdownText})</div>
            </td>
            <td class="train-platform" style="padding: 8px 8px;">
              <span class="flap-box ${platformRangeClass}" title="${platformTitle}">${platform}</span>
            </td>
            <td style="padding: 8px 10px;">
              <span class="flap-box" style="color: #38b6ff; margin-right: 6px; font-size: 0.82rem; padding: 3px 6px;">${mission}</span>
              <span class="train-dest">${dest}</span>
            </td>
            <td style="padding: 8px 10px; text-align: right;">
              <span class="flap-box ${statusClass}" style="font-size: 0.8rem; padding: 4px 8px;">${statusText.toUpperCase()}</span>
            </td>
          </tr>
        `;
      } else {
        html += `
          <tr class="train-row">
            <td class="train-time">
              <div class="train-time-main">${time}</div>
              <div class="train-countdown">(${countdownText})</div>
            </td>
            <td>
              <span class="train-platform ${platformRangeClass}" title="${platformTitle}">${platform}</span>
            </td>
            <td class="train-dest">
              <span class="train-mission">${mission}</span>
              <span style="margin-left: 6px;">${dest}</span>
            </td>
            <td class="train-status ${statusClass}">
              ${statusText}
            </td>
          </tr>
        `;
      }
    });

    tbody.innerHTML = html;
  }
}

customElements.define("domolink-transport-panel", DomolinkTransportPanel);


/**
 * Lovelace Card Custom Element
 * Permet d'insérer le tableau de bord directement dans n'importe quelle vue Lovelace.
 */
class DomolinkTransportCard extends DomolinkTransportPanel {
  constructor() {
    super();
    this._isCard = true;
    this.setAttribute("is-card", "true");
  }

  setConfig(config) {
    this._config = config || {};
    this._isCard = true;
    this.setAttribute("is-card", "true");
    if (this._config.style) {
      this._styleMode = this._config.style;
    }
    if (this._initialized && this._data) {
      this._updateDisplay();
    }
  }

  set hass(hass) {
    this._isCard = true;
    this.setAttribute("is-card", "true");
    super.hass = hass;
  }

  connectedCallback() {
    this._isCard = true;
    this.setAttribute("is-card", "true");
    super.connectedCallback();
  }

  static getStubConfig() {
    return {
      type: "custom:domolink-transport-card",
      style: "modern",
    };
  }

  static async getConfigElement() {
    return undefined;
  }

  getCardSize() {
    return 6;
  }
}
customElements.define("domolink-transport-card", DomolinkTransportCard);
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "domolink-transport-card")) {
  window.customCards.push({
    type: "domolink-transport-card",
    name: "DomoLink-Transport Card",
    description: "Panneau de gare en temps réel avec mode moderne et mécanique.",
    preview: true,
  });
}


/* =========================================================================
 * 🎆 SOCRATE RULES - EASTER EGG MODULE OFFICIEL DOMOLINK
 * ========================================================================= */
function launchSocrateRulesEasterEgg(targetRoot) {
  if (targetRoot.getElementById?.("socrate-rules-overlay") || targetRoot.querySelector?.("#socrate-rules-overlay")) return;

  if (!document.getElementById("socrate-rules-fonts")) {
    const fontLink = document.createElement("link");
    fontLink.id = "socrate-rules-fonts";
    fontLink.rel = "stylesheet";
    fontLink.href = "https://fonts.googleapis.com/css2?family=Orbitron:wght@500;900&family=Poppins:wght@300;600&display=swap";
    document.head.appendChild(fontLink);
  }

  const overlay = document.createElement("div");
  overlay.id = "socrate-rules-overlay";
  overlay.innerHTML = `
    <style>
      #socrate-rules-overlay {
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        z-index: 999999;
        background-color: #030008;
        font-family: 'Poppins', sans-serif;
        display: flex;
        justify-content: center;
        align-items: center;
        overflow: hidden;
        user-select: none;
        opacity: 0;
        transition: opacity 0.35s ease;
      }
      #socrate-rules-overlay canvas {
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 100%;
        z-index: 1;
        pointer-events: none;
      }
      #socrate-rules-overlay .socrate-container {
        position: relative;
        z-index: 10;
        text-align: center;
      }
      #socrate-rules-overlay h1.socrate-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 6rem;
        font-weight: 900;
        letter-spacing: 12px;
        text-transform: uppercase;
        display: inline-block;
        line-height: 1.1;
        filter: drop-shadow(0 0 35px rgba(0, 240, 255, 0.8));
        cursor: pointer;
      }
      #socrate-rules-overlay .socrate-letter {
        display: inline-block;
        background: linear-gradient(to bottom, #ff66b3 0%, #ff007f 35%, #7f00ff 65%, #00f0ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: socrate-wave 1.6s ease-in-out infinite;
      }
      #socrate-rules-overlay p.socrate-sub {
        font-size: 1.15rem;
        color: rgba(255, 255, 255, 0.7);
        margin-top: 25px;
        letter-spacing: 3px;
        text-transform: uppercase;
      }
      #socrate-rules-overlay p.socrate-exit-hint {
        font-size: 0.9rem;
        color: rgba(255, 255, 255, 0.5);
        margin-top: 15px;
        letter-spacing: 2px;
        cursor: pointer;
      }
      #socrate-rules-overlay p.socrate-exit-hint strong {
        color: #ff007f;
      }
      @keyframes socrate-wave {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-25px); }
      }
    </style>
    <canvas id="socrateParticleCanvas"></canvas>
    <div class="socrate-container">
      <h1 class="socrate-title" id="socrateTitle">Socrate Rules</h1>
      <p class="socrate-sub">DomoLink-Transport • Une expérience <strong>hautement philosophique</strong>.</p>
      <p class="socrate-exit-hint" id="socrateExitHint">Cliquez 3 fois sur <strong>SOCRATE RULES</strong> pour fermer</p>
    </div>
  `;

  targetRoot.appendChild(overlay);
  requestAnimationFrame(() => { overlay.style.opacity = "1"; });

  const canvas = overlay.querySelector("#socrateParticleCanvas");
  const ctx = canvas.getContext("2d");
  const title = overlay.querySelector("#socrateTitle");
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;

  const lines = ["Socrate", "Rules"];
  title.innerHTML = "";
  let idx = 0;
  lines.forEach((l) => {
    const d = document.createElement("div");
    [...l].forEach((c) => {
      const s = document.createElement("span");
      s.textContent = c;
      s.classList.add("socrate-letter");
      s.style.animationDelay = `${idx * 0.08}s`;
      d.appendChild(s);
      idx++;
    });
    title.appendChild(d);
  });

  // Particle animation
  const particles = [];
  for (let i = 0; i < 150; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 1.5,
      vy: (Math.random() - 0.5) * 1.5,
      size: Math.random() * 3 + 1,
      color: ["#ff007f", "#7f00ff", "#00f0ff"][Math.floor(Math.random() * 3)],
    });
  }

  let animRunning = true;
  function loop() {
    if (!animRunning) return;
    ctx.fillStyle = "rgba(3, 0, 8, 0.2)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    particles.forEach(p => {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
      if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.fill();
    });
    requestAnimationFrame(loop);
  }
  loop();

  // Exit trigger
  let exitClicks = 0;
  const exitHandler = () => {
    exitClicks++;
    if (exitClicks >= 3) {
      animRunning = false;
      overlay.style.opacity = "0";
      setTimeout(() => overlay.remove(), 400);
    }
  };
  title.addEventListener("click", exitHandler);
  overlay.querySelector("#socrateExitHint").addEventListener("click", () => {
    animRunning = false;
    overlay.style.opacity = "0";
    setTimeout(() => overlay.remove(), 400);
  });
}
