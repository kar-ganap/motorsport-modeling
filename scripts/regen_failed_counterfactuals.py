"""
Regenerate the 5 counterfactual files with position mismatches.
"""

from scripts.precompute_counterfactuals import process_race_counterfactuals

# The 5 races with wrong positions (generated before the fix)
failed_races = [
    ('sebring', 'race2', 20),
    ('sonoma', 'race1', 20),
    ('sonoma', 'race2', 20),
    ('vir', 'race1', 20),
    ('vir', 'race2', 20),
]

print('='*80)
print('REGENERATING 5 COUNTERFACTUAL FILES WITH POSITION MISMATCHES')
print('='*80)
print()

for track, race, num_laps in failed_races:
    print(f'\nProcessing: {track}/{race}...')
    success = process_race_counterfactuals(track, race, num_laps)
    if success:
        print(f'✓ Successfully regenerated {track}/{race}')
    else:
        print(f'✗ FAILED to regenerate {track}/{race}')

print()
print('='*80)
print('REGENERATION COMPLETE')
print('='*80)
