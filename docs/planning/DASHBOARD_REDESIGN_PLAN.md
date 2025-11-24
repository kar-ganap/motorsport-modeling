# Dashboard Redesign Plan

## Current Issues Identified

### 1. Header
- ❌ Toyota Gazoo Racing text not visible (white on white)
- Status: CSS applied but not rendering

### 2. Layout & Proportions
- ❌ Forecast column too wide (currently 1:1.5 ratio)
- ❌ Heights of Forecast and Race Context sections don't match
- Target: Forecast narrower, Race Context wider (e.g., 1:2 ratio)

### 3. Field Forecast Chart
- ❌ Y-axis shows driver numbers (#23, #45, etc.) - not intuitive
- ❌ Bars still appear thin/sparse despite width=0.9
- ❌ No clear indication which driver is "YOU"
- Target:
  - Relative position labels: -2, -1, YOU, +1, +2
  - Wider, more prominent bars
  - Clear visual hierarchy

### 4. Race Context Visualizations
- ❌ Primitive looking plots (basic Plotly defaults)
- ❌ Three subplots crammed together without clear separation
- ❌ No individual titles/borders for each subplot
- ❌ Poor use of color and visual design
- Target:
  - Individual borders and backgrounds for each subplot
  - Clear subtitles for each visualization
  - Modern color schemes and styling
  - Better use of space and visual hierarchy

## Implementation Plan

### Phase 1: Fix Header (PRIORITY 1)
- [ ] 1.1: Add explicit white color to header span using inline style override
- [ ] 1.2: Test if CSS selector needs to be more specific
- [ ] 1.3: Verify text is visible after reload

### Phase 2: Adjust Layout Proportions (PRIORITY 2)
- [ ] 2.1: Change column ratio from [1, 1.5] to [1, 2]
- [ ] 2.2: Set explicit heights for both sections (e.g., 600px)
- [ ] 2.3: Ensure vertical alignment matches

### Phase 3: Redesign Field Forecast (PRIORITY 3)
- [ ] 3.1: Modify data to include relative positions
- [ ] 3.2: Update y-axis labels to show -2, -1, YOU, +1, +2
- [ ] 3.3: Add gradient colors (green for behind, blue for YOU, red for ahead)
- [ ] 3.4: Increase bar width to 0.95
- [ ] 3.5: Add better visual emphasis on focused driver
- [ ] 3.6: Reduce overall chart height to 400px (to fit narrower column)

### Phase 4: Modernize Race Context (PRIORITY 4)
- [ ] 4.1: Create separate subplot for Gap Evolution with:
  - [ ] Individual border and background
  - [ ] Clear subtitle "Gap Analysis"
  - [ ] Modern color gradient
  - [ ] Fill areas under curves
- [ ] 4.2: Create separate subplot for Sector Deltas with:
  - [ ] Individual border and background
  - [ ] Clear subtitle "Sector Performance"
  - [ ] Color-coded bars (red/green)
  - [ ] Better spacing
- [ ] 4.3: Create separate subplot for Position Timeline with:
  - [ ] Individual border and background
  - [ ] Clear subtitle "Race Position"
  - [ ] Battle markers more prominent
  - [ ] Smoother line styling
- [ ] 4.4: Set consistent height (600px total) to match forecast section

### Phase 5: Polish & Final Touches (PRIORITY 5)
- [ ] 5.1: Add subtle animations/transitions
- [ ] 5.2: Ensure all fonts are consistent
- [ ] 5.3: Add hover effects where appropriate
- [ ] 5.4: Test on multiple screen sizes
- [ ] 5.5: Final QA pass

## Technical Notes

### Key Files
- `dashboard.py` - Main dashboard file
  - Lines 86-145: CSS styling
  - Lines 439-505: `create_compact_prediction_chart()` - Field forecast
  - Lines 246-436: `create_combined_race_context()` - Race context charts
  - Lines 679-726: Layout structure

### Dependencies
- Plotly for charts (already installed)
- Consider adding plotly.graph_objects advanced features

### Testing Strategy
- After each phase, reload dashboard and verify changes
- Use `touch dashboard.py` to trigger auto-reload
- Test with actual race data (Indianapolis Race 1)

## Success Criteria
- ✓ Toyota text clearly visible in header
- ✓ Forecast column narrower, race context wider
- ✓ Forecast chart shows relative positions (-2 to +2)
- ✓ Each race context subplot has clear border and subtitle
- ✓ Overall aesthetic is modern and professional
- ✓ Heights match between sections
