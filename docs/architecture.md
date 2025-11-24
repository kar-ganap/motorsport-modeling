# RaceIQ - System Architecture

## Executive Summary

RaceIQ is a comprehensive motorsport analytics platform that transforms raw telemetry data into actionable coaching insights through three integrated analytical approaches:

1. **Real-Time Analytics** - Lap-by-lap coaching during race simulation
2. **Comparative Analysis** - Beat-the-driver-ahead explanations
3. **Counterfactual Analysis** - What-if scenario modeling

This document details the complete system architecture, data flows, and technical implementation.

---

## System Overview

```mermaid
graph TB
    subgraph "Data Layer"
        RAW[Raw Telemetry Data<br/>14 races × 20 laps × ~25 drivers]
        LAP[Lap Times CSV]
        GPS[GPS Coordinates<br/>Selected tracks]
    end

    subgraph "Processing Layer"
        LOADER[Telemetry Loader<br/>Multi-format support]
        FEAT[Feature Engineering<br/>Tire deg, traffic, pace]
        METRICS[Performance Metrics<br/>Brake, throttle, G-force]
    end

    subgraph "Analytics Engines"
        REAL[Real-Time Coach<br/>State monitoring]
        COMP[Comparative<br/>Beat-the-ahead]
        COUNT[Counterfactual<br/>What-if scenarios]
        PRED[Predictive Models<br/>Lap time, position]
    end

    subgraph "Presentation Layer"
        DASH[Interactive Dashboard<br/>3 specialized pages]
        VIZ[Visualizations<br/>Plotly charts]
        NARR[AI Narratives<br/>GPT-4o summaries]
    end

    RAW --> LOADER
    LAP --> LOADER
    GPS --> LOADER
    LOADER --> FEAT
    LOADER --> METRICS

    FEAT --> REAL
    FEAT --> COMP
    FEAT --> COUNT
    FEAT --> PRED

    METRICS --> REAL

    REAL --> DASH
    COMP --> DASH
    COUNT --> DASH
    PRED --> DASH

    DASH --> VIZ
    DASH --> NARR
```

---

## Data Architecture

### Data Formats Handled

RaceIQ supports three distinct telemetry formats across the GR Cup dataset:

```mermaid
graph LR
    subgraph "Format Detection"
        INPUT[Race Directory]
        DETECT{Format Type?}
        LONG[Long Format CSV<br/>signal,value pairs]
        WIDE[Wide Format CSV<br/>columns per signal]
        JSON[JSON with Arrays<br/>nested structure]
    end

    INPUT --> DETECT
    DETECT -->|Most tracks| LONG
    DETECT -->|Some tracks| WIDE
    DETECT -->|Sebring| JSON

    LONG --> PIVOT[Pivot to Wide]
    WIDE --> VALIDATE[Validate Columns]
    JSON --> PARSE[Parse & Flatten]

    PIVOT --> UNIFIED[Unified DataFrame]
    VALIDATE --> UNIFIED
    PARSE --> UNIFIED
```

### Data Quality Pipeline

```mermaid
flowchart TD
    START[Raw Telemetry] --> CHECK1{Valid lap #?}
    CHECK1 -->|lap < 32768| CHECK2{Has lap time?}
    CHECK1 -->|Invalid| SKIP1[Skip corrupt lap]

    CHECK2 -->|Yes| CHECK3{Required signals?}
    CHECK2 -->|No| SKIP2[Skip lap]

    CHECK3 -->|speed, throttle, brake| CLEAN[Clean Data]
    CHECK3 -->|Missing critical| SKIP3[Skip/Warn]

    CLEAN --> IMPUTE[Handle Missing Values]
    IMPUTE --> OUTPUT[Clean Telemetry]
```

**Handled Edge Cases:**
- Lap 32768 corruption (Sebring)
- Missing GPS data (VIR, Barber, Mid-Ohio)
- Inconsistent signal naming (pbrake_f vs brake_pressure)
- JSON vs CSV format variations
- Partial lap data

---

## Feature Engineering Architecture

### Tier 1: Driver Profiling Features

**Purpose:** Stable characteristics that define a driver's skill level

```mermaid
graph TB
    subgraph "Baseline Computation"
        TEL[Telemetry<br/>Laps 1-5]

        TEL --> BRAKE[Braking Smoothness<br/>CV of peak brake force]
        TEL --> THROTTLE[Throttle Timing<br/>Lift-off count]
        TEL --> GFORCE[G-Force Utilization<br/>Corner speed]
        TEL --> COAST[Coasting %<br/>Efficiency]
    end

    subgraph "Profile Characteristics"
        BRAKE --> PROFILE[Driver Profile]
        THROTTLE --> PROFILE
        GFORCE --> PROFILE
        COAST --> PROFILE

        PROFILE --> STABLE[High cross-driver variance<br/>Low within-driver variance]
    end
```

**Validation:** Ratio > 1.5 (cross-driver std / within-driver std)

### Tier 2: State Monitoring Features

**Purpose:** Detect real-time changes during race

```mermaid
graph TB
    subgraph "Lap-by-Lap Analysis"
        CURRENT[Current Lap<br/>Lap N]

        CURRENT --> DEG[Tire Degradation<br/>Pace vs baseline]
        CURRENT --> CONS[Consistency<br/>Lap time variance]
        CURRENT --> TECH[Technique Drift<br/>vs profile baseline]
    end

    subgraph "State Detection"
        DEG --> ALERT1{Exceeds<br/>threshold?}
        CONS --> ALERT2{Exceeds<br/>threshold?}
        TECH --> ALERT3{Exceeds<br/>threshold?}

        ALERT1 -->|Yes| COACH[Coaching Alert]
        ALERT2 -->|Yes| COACH
        ALERT3 -->|Yes| COACH
    end
```

### Race-Level Features

```mermaid
graph LR
    subgraph "Stint Analysis"
        LAPS[All Race Laps] --> EARLY[Early Pace<br/>Laps 1-5]
        LAPS --> MID[Mid Pace<br/>Laps 6-15]
        LAPS --> LATE[Late Pace<br/>Lap 16+]
    end

    subgraph "Degradation"
        EARLY --> SLOPE[Linear Regression<br/>Lap vs Time]
        MID --> SLOPE
        LATE --> SLOPE
        SLOPE --> DEGRATE[Degradation Rate<br/>s/lap]
    end

    subgraph "Traffic"
        LAPS --> TRAFFIC[Traffic Detection<br/>Gap changes]
        TRAFFIC --> COST[Traffic Cost<br/>Total seconds lost]
    end
```

---

## Analytics Engines

### 1. Real-Time Coaching System

```mermaid
sequenceDiagram
    participant User
    participant UI as Dashboard
    participant Monitor as StateMonitor
    participant Profile as DriverProfile
    participant Telemetry

    User->>UI: Select driver, start race
    UI->>Telemetry: Load race data
    UI->>Profile: Build baseline (laps 1-5)

    loop Each Lap
        UI->>Monitor: Process lap N
        Monitor->>Telemetry: Get lap N data
        Monitor->>Monitor: Compare vs baseline
        Monitor->>Monitor: Detect anomalies
        Monitor->>UI: Return alerts
        UI->>User: Display coaching message
    end
```

**Alert Types:**
- 🔴 Critical: Degradation >0.1s/lap vs field
- 🟡 Warning: Technique drift >2σ from baseline
- 🟢 Advisory: Traffic detected, pace maintained

### 2. Comparative Analysis (Beat-the-Driver-Ahead)

```mermaid
flowchart TD
    START[Race Results] --> SORT[Sort by finish position]
    SORT --> ITERATE[For each driver]

    ITERATE --> AHEAD{Who finished<br/>directly ahead?}

    AHEAD -->|P1| P2[Compare to P2<br/>Why we won]
    AHEAD -->|Other| PN[Compare to P(N-1)<br/>Why we lost]

    P2 --> ANALYZE[Analyze differences]
    PN --> ANALYZE

    ANALYZE --> PACE[Pace delta<br/>by stint]
    ANALYZE --> DEG[Degradation<br/>delta]
    ANALYZE --> TRAFFIC[Traffic<br/>delta]

    PACE --> ROOT[Identify root cause]
    DEG --> ROOT
    TRAFFIC --> ROOT

    ROOT --> QUANT[Quantify gap<br/>in seconds]
    QUANT --> GPT[GPT-4o narrative]
```

**Key Innovation:** Instead of comparing to field average, each driver is compared to the specific person who beat them, making insights immediately actionable.

### 3. Counterfactual Analysis

```mermaid
graph TB
    subgraph "Scenario Generation"
        DRIVER[Driver Performance] --> ACTUAL[Actual metrics]

        ACTUAL --> SIM1[Scenario: Match top-5 degradation]
        ACTUAL --> SIM2[Scenario: Match median consistency]
        ACTUAL --> SIM3[Scenario: Remove traffic]
        ACTUAL --> SIM4[Scenario: Combined improvements]
    end

    subgraph "Position Prediction"
        SIM1 --> PRED1[Predicted position]
        SIM2 --> PRED2[Predicted position]
        SIM3 --> PRED3[Predicted position]
        SIM4 --> PRED4[Predicted position]
    end

    subgraph "Recommendations"
        PRED1 --> RANK[Rank by impact]
        PRED2 --> RANK
        PRED3 --> RANK
        PRED4 --> RANK

        RANK --> TOP[Top recommendation:<br/>Biggest position gain]
    end
```

**Model:** Gradient Boosting Regressor trained on race features → final position

---

## Predictive Modeling

### Model Pipeline

```mermaid
graph LR
    subgraph "Training Data"
        HIST[Historical races<br/>13 races] --> SPLIT[Train/Test Split<br/>Leave-one-out]
    end

    subgraph "Features"
        SPLIT --> F1[Pace metrics<br/>early/mid/late]
        SPLIT --> F2[Degradation rate]
        SPLIT --> F3[Consistency]
        SPLIT --> F4[Traffic impact]
        SPLIT --> F5[Driver baseline]
    end

    subgraph "Models"
        F1 --> LAP[Lap Time<br/>Linear Regression]
        F1 --> POS[Position<br/>Gradient Boosting]

        F2 --> LAP
        F2 --> POS

        F3 --> LAP
        F3 --> POS

        F4 --> POS
        F5 --> POS
    end

    subgraph "Validation"
        LAP --> VAL[Cross-validation<br/>14 races]
        POS --> VAL
        VAL --> METRICS[MAE, R², Position accuracy]
    end
```

### Model Selection Rationale

| Model Type | Use Case | Rationale |
|------------|----------|-----------|
| Linear Regression | Lap time prediction | Linear relationship between features and lap time; interpretable coefficients |
| Gradient Boosting | Position prediction | Handles non-linear effects (e.g., tire strategy, traffic); robust to outliers |
| Statistical Analysis | Degradation rate | Simple linear fit captures tire wear trend |

---

## Dashboard Architecture

### Page Structure

```mermaid
graph TB
    subgraph "Multi-Page Dashboard"
        HOME[Dashboard.py<br/>Landing page]

        HOME --> PAGE1[Race Analytics<br/>Real-time coaching]
        HOME --> PAGE2[Race Insights<br/>Post-race analysis]
        HOME --> PAGE3[Model Validation<br/>Performance metrics]
    end

    subgraph "Race Analytics Components"
        PAGE1 --> NOW[NOW: Current state<br/>Position, gaps, lap time]
        PAGE1 --> NEXT[NEXT: Predictions<br/>Next lap forecast]
        PAGE1 --> CONTEXT[CONTEXT: Race dynamics<br/>Sector times, field position]
        PAGE1 --> DIAG[DIAGNOSTICS: Issues<br/>Conditional alerts]
        PAGE1 --> RADIO[RADIO: Coaching<br/>Actionable message]
    end

    subgraph "Race Insights Components"
        PAGE2 --> COMP[Comparative Tab<br/>Beat-the-ahead analysis]
        PAGE2 --> COUNT[Counterfactual Tab<br/>What-if scenarios]
        PAGE2 --> NARR[AI Narratives<br/>GPT-4o summaries]
    end

    subgraph "Model Validation"
        PAGE3 --> ACC[Accuracy Metrics<br/>MAE, R², Position error]
        PAGE3 --> VIS[Visualizations<br/>Predicted vs Actual]
        PAGE3 --> DRIVER[Per-Driver Breakdown<br/>Model performance]
    end
```

### State Management

```mermaid
stateDiagram-v2
    [*] --> SelectRace: User chooses track/race
    SelectRace --> LoadData: Click "Start"

    LoadData --> Loading: Show spinner (1-2 min)
    Loading --> Ready: Data loaded

    Ready --> Running: Auto-advance laps
    Running --> Running: Process next lap
    Running --> Complete: Lap 20 reached

    Complete --> [*]

    note right of Loading
        Loads 247k rows of telemetry
        Builds driver profiles
        Initializes monitors
    end note

    note right of Running
        Updates every 2s / sim_speed
        Generates coaching alerts
        Updates visualizations
    end note
```

---

## Performance Optimizations

### Data Loading Strategy

**Challenge:** Loading full telemetry for 25 drivers × 20 laps takes ~120 seconds

**Solution:** Lazy loading with precomputed analytics

```mermaid
flowchart LR
    subgraph "Initial Load (Fast)"
        A[Page Load] --> B[Race Features<br/>Parquet file]
        B --> C[Display selector<br/><1 second]
    end

    subgraph "On Demand (Slow)"
        D[User clicks Start] --> E[Load Telemetry<br/>~120 seconds]
        E --> F[Build Profiles<br/>~5 seconds]
        F --> G[Start Simulation]
    end

    C -.->|User action| D
```

### Precomputation Strategy

**Files precomputed for all 14 races:**

1. `{track}_{race}_comparative.parquet` - Beat-the-ahead analysis with GPT-4o narratives
2. `{track}_{race}_counterfactual.parquet` - What-if scenarios with position predictions

**Benefits:**
- Race Insights tab loads instantly
- No API calls during user session
- Consistent narratives across page refreshes

---

## AI Integration

### Narrative Generation Pipeline

```mermaid
sequenceDiagram
    participant Metrics as DriverMetrics
    participant Builder as PromptBuilder
    participant GPT as GPT-4o API
    participant Cache as Parquet Cache

    Metrics->>Builder: Driver performance data
    Builder->>Builder: Build structured prompt

    alt For P1 (Winner)
        Builder->>GPT: Compare to P2: Why did we win?
    else For Others
        Builder->>GPT: Compare to P(N-1): Why did we lose?
    end

    GPT->>GPT: Generate 2-3 sentence analysis
    GPT->>Cache: Store narrative

    Note over Cache: Precomputed for all drivers
    Cache->>Dashboard: Instant retrieval
```

### Prompt Engineering

**System Prompt Principles:**
1. **Data-driven**: Base insights strictly on provided metrics
2. **Specific**: Provide concrete numbers, not vague statements
3. **Professional**: Use motorsport terminology
4. **Concise**: 2-3 sentences maximum
5. **Actionable**: Focus on technical factors (tire management, setup)

**Avoid:**
- "Push harder" or "try harder" advice
- Emotional language or excessive praise
- Speculation about factors not in data

---

## Technology Stack

### Core Libraries

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Data Processing | pandas, numpy | Telemetry manipulation, feature engineering |
| Visualization | Plotly, Matplotlib | Interactive charts, track maps |
| ML Models | scikit-learn | Regression, gradient boosting |
| Dashboard | Streamlit | Multi-page web interface |
| AI Narratives | OpenAI GPT-4o | Natural language summaries |
| Geospatial | Shapely | GPS racing line analysis |

### Deployment Architecture

```mermaid
graph TB
    subgraph "Local Development"
        DEV[Developer Machine] --> UV[uv Package Manager]
        UV --> VENV[Virtual Environment]
        VENV --> RUN[streamlit run Dashboard.py]
    end

    subgraph "Production (Future)"
        CLOUD[Streamlit Cloud] --> DEPLOY[Auto-deploy from GitHub]
        DEPLOY --> APP[Hosted Application]
        APP --> CACHE[Precomputed Data<br/>CDN-cached parquet]
    end

    RUN -.->|Push to GitHub| CLOUD
```

---

## Scalability Considerations

### Current Limitations

1. **Memory:** Full telemetry for one race: ~47MB in memory
2. **Compute:** Profile building: ~5 seconds for 25 drivers
3. **Storage:** Parquet files: ~2MB per race (compressed)

### Future Optimizations

```mermaid
graph TB
    subgraph "Data Storage"
        CURRENT[Current: CSV files<br/>~500MB raw] --> FUTURE1[Future: Parquet format<br/>~50MB compressed]
    end

    subgraph "Computation"
        SEQ[Sequential processing] --> PAR[Parallel driver profiling<br/>4x speedup]
    end

    subgraph "Caching"
        NONE[No caching] --> REDIS[Redis cache<br/>Sub-second retrieval]
    end
```

---

## Testing & Validation

### Data Validation

```mermaid
flowchart TD
    START[New Race Data] --> CHECK1{All 14 races<br/>present?}
    CHECK1 -->|No| FAIL1[Missing race data]
    CHECK1 -->|Yes| CHECK2{Parquet files<br/>generated?}

    CHECK2 -->|No| FAIL2[Precompute failed]
    CHECK2 -->|Yes| CHECK3{Required columns<br/>present?}

    CHECK3 -->|No| FAIL3[Schema mismatch]
    CHECK3 -->|Yes| CHECK4{Narratives<br/>generated?}

    CHECK4 -->|No| FAIL4[GPT-4o error]
    CHECK4 -->|Yes| PASS[Ready for deployment]
```

### Model Validation

**Cross-validation approach:** Leave-one-race-out

- Train on 13 races
- Validate on 1 held-out race
- Repeat for all 14 races
- Report aggregate metrics

**Metrics tracked:**
- Position prediction: Mean Absolute Error
- Lap time prediction: R² score
- Top-5 accuracy: Binary classification

---

## Security & Privacy

### Data Handling

- **No PII:** Only vehicle numbers (anonymous)
- **API Keys:** Environment variables, never committed
- **Local Storage:** Data stays on user's machine in development

### Future Considerations

- OAuth authentication for hosted version
- Rate limiting on GPT-4o API calls
- Data encryption at rest

---

## Summary

RaceIQ demonstrates a complete motorsport analytics stack:

1. **Robust Data Pipeline:** Handles 3 telemetry formats, 14 races, multiple tracks
2. **Sophisticated Analytics:** Real-time, comparative, and counterfactual approaches
3. **Production-Ready UI:** Lazy loading, precomputation, responsive design
4. **AI Integration:** GPT-4o generates professional coaching narratives
5. **Validated Models:** Cross-validated predictions across all races

**Key Technical Achievements:**
- Multi-format telemetry loader with automatic detection
- Two-tier feature architecture (profile vs. state)
- Beat-the-driver-ahead comparative framework
- Precomputed analytics for instant page loads
- Integrated AI narrative generation

**Next Steps:**
- Deploy to Streamlit Cloud
- Add real-time data ingestion
- Expand to more race series
- Mobile-responsive design
