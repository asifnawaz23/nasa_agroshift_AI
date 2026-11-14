# FieldShift Planner — Start Sequence (who starts first)

Companion to `FIELD_SHIFT_TEAM_PLAN.md` (v2). This file covers **the first 8 hours**: who starts first, in what order, and how work moves between computers. After hour 8, everyone follows their own hour-by-hour table in the main plan (section 15).

## Setup
| Computer | People |
|---|---|
| **Shared PC** | Abdul Rehman, Aman, Asif (backend) |
| **Shayan's PC** | Shayan (backend lead, merges to `main`) |
| **Frontend PCs** | Talha, Musab |

---

## 1. Who unblocks whom

```
Aman (AppEEARS + POWER sample) ─┐
                                 ├─▶ Asif (climate engine) ─▶ Shayan (/analyze) ─▶ Frontend (real data at hour 8)
Shayan (repo + mock JSON) ──────┤
                                 └─▶ Frontend (starts on the mock right away)
Abdul Rehman (crop table) ──────────▶ Shayan (seed + scoring) + Talha (crop dropdowns)
```

**Start first:** **Shayan** (repo + mock JSON) and **Aman** (AppEEARS requests). Everything else waits on them, so both start in the first 15 minutes.

---

## 2. First 2 hours, minute by minute

| Time | Shayan (own PC) | Shared PC (Aman / Asif / Abdul Rehman) | Frontend (Talha, Musab) |
|---|---|---|---|
| **0:00–0:15** | Create GitHub repo, invite everyone, push empty folder structure | **Aman:** Earthdata login, **submit AppEEARS requests** (SMAP 2015–2025 + NDVI 2006–2025, 3 pins). First thing on the shared PC: the queue takes hours | Install Node, wait for repo invite |
| **0:15–0:45** | Write and push `docs/mock_analyze.json` + `docs/API_CONTRACT.md` | **Aman:** download one NASA POWER daily file for Iowa (42.0, -93.6) → `sample_power_iowa.csv` | Clone repo. **Talha:** Vite scaffold. **Musab:** recharts setup |
| **0:45–1:00** | Django skeleton + `/api/health/` | Clone repo, **push** `engine/tests/sample_power_iowa.csv` → Asif unblocked | Load mock JSON. **Talha:** check Urdu voice support in Chrome |
| **1:00–2:00** | Models + migrations | **Asif:** write and push `engine/tests/sample_profile.json` + `engine/constants.py` → Shayan's scoring unblocked | Map (Talha), ClimateChart (Musab) |

---

## 3. Shared PC: driver rotation (hours 0–8)

Only one person types at a time. The other two work **off-keyboard** (phone, paper, a second laptop if available) to prepare their next turn.

| Hours | At the keyboard | Off-keyboard |
|---|---|---|
| **0–1** | **Aman:** AppEEARS, POWER sample, push | **Asif:** ET0 and stress formulas on paper (remember ET0 × 0.408). **Abdul Rehman:** research crop water needs and seasons on phone (FAO-56, FAO Paper 33, Pakistan kharif/rabi) |
| **1–2** | **Asif:** `sample_profile.json` + `constants.py`, push | **Abdul Rehman:** finish crop list draft (12–15 crops + sources + Urdu names). **Aman:** plan `power.py` |
| **2–3** | **Abdul Rehman:** type `crops.csv`, push, **send crop slugs to Talha** | **Asif:** plan notebook code. **Aman:** read SoilGrids API docs |
| **3–5** | **Aman:** `power.py` + `cache.py`, push | **Asif:** prepare climatology code. **Abdul Rehman:** calendars + growth stages + rotation templates on paper; start PRISM / CDL downloads on phone |
| **5–6** | **Asif:** `build_climate_profile()` v1, **push by hour 6** | **Abdul Rehman + Aman:** check Asif's numbers against the sample |
| **6–8** | 🔗 **Integration with Shayan:** Asif and Aman fix mismatches together | **Abdul Rehman:** `crop_calendars.csv`, `rotation_templates.json`, then PRISM / CDL / SSURGO for Iowa |
| **8+** | Rotate every 1–2 hours, following section 15 of the main plan | |

**If anyone brings a second laptop, give it to Abdul Rehman.** His work (crop CSVs, Iowa downloads) is the most independent, so Aman and Asif keep the main PC.

---

## 4. Key handoffs

| When | From → To | What | Why it matters |
|---|---|---|---|
| ~0:45 | Aman → Asif | `sample_power_iowa.csv` | Asif can't build the engine without real data |
| ~1:00 | Shayan → Frontend | `mock_analyze.json` | Frontend builds the whole UI on it until hour 8 |
| ~2:00 | Shayan ← Asif | `sample_profile.json` | Shayan writes scoring without waiting for the real engine |
| ~2:00 | Abdul Rehman → Talha + Shayan | Crop slugs + `crops.csv` | Same crop names in dropdowns and scoring |
| ~5:00 | Aman → Shayan | `power.py` + `cache.py` | `/analyze` needs live data |
| **~6:00** | **Asif → Shayan** | **Climate profile v1** | **Most important handoff of the day** |
| ~8:00 | Shayan → Frontend | Working `/api/analyze/` | Frontend switches from mock to real data |

---

## 5. Git rules for the shared PC

1. **One branch per person per task:** `feat/aman-power`, `feat/asif-climate`, `feat/abdul-crops`.
2. **Before switching drivers:** commit and push everything.
   ```bash
   git status
   ```
   ```bash
   git add -A
   ```
   ```bash
   git commit -m "Aman: power.py fetcher"
   ```
   ```bash
   git push
   ```
3. **Next driver:** update and switch to their own branch.
   ```bash
   git checkout main
   ```
   ```bash
   git pull
   ```
   ```bash
   git checkout -b feat/asif-climate
   ```
4. Put your **name at the start of each commit message**, since all commits come from the same computer.
5. After each push, **post in the group chat:** "Pushed X on branch Y, Shayan please merge."
6. Shayan merges to `main`; everyone else pulls `main` before starting a new task.

---

## 6. Check-ins

| Hour | Who | What |
|---|---|---|
| 3 | Backend (4) | Is the POWER sample, sample profile and crop table in? |
| 4 | Everyone | Frontend shows mock data; backend skeleton deployed? |
| 6 | Backend (4) | Climate profile v1 handed to Shayan? |
| **8** | **Everyone** | **M2: real `/api/analyze/` works for Iowa, frontend switches to real data** |

**Blocked for more than 30 minutes?** Post in the group chat immediately.
