# Unit Test Report

Blood Bank & Donation Management System (BBMS), Team T9.

This report covers the automated unit tests (`tests/unit`, one module at a time with
fakes for its neighbours) and the integration tests (`tests/integration`, the fully wired
FastAPI app on a temporary database). System tests are in the System Validation Report.

## 1. Test run

- Date of run: 20-11-2026 14:00
- Code under test: branch `feature/test-reports-docs`, commit `1841697` plus uncommitted changes
- Python 3.14.8 on Linux, pytest 8.4.2, coverage.py 7.16.2
- Database: SQLite, a new empty database for every test
- Produced by `python scripts/generate_test_reports.py`

## 2. Summary

| Suite | Tests | Passed | Failed | Skipped | Time |
|---|---|---|---|---|---|
| Unit | 271 | 271 | 0 | 0 | 0.9 s |
| Integration | 61 | 61 | 0 | 0 | 8.8 s |
| **Total** | **332** | **332** | **0** | **0** | **9.7 s** |

## 3. Unit tests by file

| Test file | Covers | Tests | Passed | Failed |
|---|---|---|---|---|
| `test_approve_dispatch.py` | Approve / reject / dispatch a request (BBS-F-032, BBS-SR-004) | 19 | 19 | 0 |
| `test_compatibility.py` | Blood group compatibility rules (BBS-F-031) | 74 | 74 | 0 |
| `test_cross_match.py` | Cross-match and allocation in the request service (BBS-F-031, BBS-NF-005) | 20 | 20 | 0 |
| `test_donation_history.py` | Donation history (BBS-F-012) | 18 | 18 | 0 |
| `test_drives.py` | Drives, slot booking, reminders (BBS-F-040, 041, 042) | 9 | 9 | 0 |
| `test_eligibility_check.py` | Donor eligibility rules (BBS-F-011) | 42 | 42 | 0 |
| `test_emergency_callout.py` | Emergency donor call-out (BLOOD-26) | 2 | 2 | 0 |
| `test_inventory_blood12.py` | Unique blood bag IDs (BBS-F-020) | 6 | 6 | 0 |
| `test_inventory_blood13.py` | Component type and expiry date (BBS-F-021) | 14 | 14 | 0 |
| `test_inventory_blood14.py` | Automatic expiry and audit (BBS-F-022, BBS-SR-004) | 12 | 12 | 0 |
| `test_inventory_cross_match.py` | Inventory side of cross-match (BBS-F-031, BBS-NF-005) | 7 | 7 | 0 |
| `test_low_stock.py` | Low-stock alerts (BLOOD-25) | 12 | 12 | 0 |
| `test_record_donation.py` | Recording a donation end to end (BBS-F-011, 012, 020) | 9 | 9 | 0 |
| `test_submit_blood_request.py` | Submitting a hospital request (BBS-F-030) | 27 | 27 | 0 |

## 4. Integration tests by file

| Test file | Covers | Tests | Passed | Failed |
|---|---|---|---|---|
| `test_account_lockout.py` | Account lockout after 5 wrong passwords (BBS-F-003) | 4 | 4 | 0 |
| `test_admin_accounts_api.py` | Admin creates staff / hospital / admin accounts (BBS-F-001) | 4 | 4 | 0 |
| `test_auth_api.py` | Login, identity, logout, role checks (BBS-F-001, BBS-SR-003) | 10 | 10 | 0 |
| `test_dashboard_actions_api.py` | Every write action the React dashboards make | 16 | 16 | 0 |
| `test_demo_seed.py` | Demo data loads every dashboard | 5 | 5 | 0 |
| `test_donor_profile_api.py` | Donor profile (BBS-F-010) | 3 | 3 | 0 |
| `test_emergency_callout_api.py` | Emergency donor call-out API (BLOOD-26) | 3 | 3 | 0 |
| `test_low_stock_api.py` | Low-stock alerts API (BLOOD-25) | 3 | 3 | 0 |
| `test_request_dispatch_flow.py` | Request -> cross-match -> dispatch across modules (BBS-F-030..032) | 7 | 7 | 0 |
| `test_signup_api.py` | Signup with OTP (BBS-F-002) | 3 | 3 | 0 |
| `test_signup_rules.py` | OTP expiry, attempt limit, delivery failure (BBS-F-002) | 3 | 3 | 0 |

## 5. Failures

None. Every test passed.

## 6. How to reproduce

```bash
python -m pytest tests/unit -v
python -m pytest tests/integration -v
```

The same two commands run in GitHub Actions (`.github/workflows/CI.yml`, job `test`) on
every pull request into `main`. Raw results: `docs/raw/unit.xml`, `docs/raw/integration.xml`.

## Appendix A. Every unit test

| Test file | Test | Result |
|---|---|---|
| `test_approve_dispatch` | `test_api_invalid_transition_is_409` | PASS |
| `test_approve_dispatch` | `test_api_missing_request_is_404` | PASS |
| `test_approve_dispatch` | `test_api_queue_rejects_unknown_status` | PASS |
| `test_approve_dispatch` | `test_api_reject_needs_reason` | PASS |
| `test_approve_dispatch` | `test_api_staff_endpoints_reject_other_roles` | PASS |
| `test_approve_dispatch` | `test_api_staff_full_flow` | PASS |
| `test_approve_dispatch` | `test_approve_moves_pending_to_approved_and_logs_actor` | PASS |
| `test_approve_dispatch` | `test_cannot_decide_a_request_twice[approve-approve]` | PASS |
| `test_approve_dispatch` | `test_cannot_decide_a_request_twice[approve-reject]` | PASS |
| `test_approve_dispatch` | `test_cannot_decide_a_request_twice[reject-approve]` | PASS |
| `test_approve_dispatch` | `test_cannot_dispatch_before_approval` | PASS |
| `test_approve_dispatch` | `test_dispatch_marks_the_allocated_units_as_sent` | PASS |
| `test_approve_dispatch` | `test_dispatch_refused_when_allocated_units_are_unavailable` | PASS |
| `test_approve_dispatch` | `test_dispatched_request_is_final` | PASS |
| `test_approve_dispatch` | `test_full_flow_pending_approved_dispatched` | PASS |
| `test_approve_dispatch` | `test_queue_lists_only_requested_status_oldest_first` | PASS |
| `test_approve_dispatch` | `test_reject_requires_pending_and_keeps_reason` | PASS |
| `test_approve_dispatch` | `test_staff_actions_on_missing_request_raise` | PASS |
| `test_approve_dispatch` | `test_transition_only_applies_from_expected_status` | PASS |
| `test_compatibility` | `test_a_positive_request_never_gets_b_negative[Plasma]` | PASS |
| `test_compatibility` | `test_a_positive_request_never_gets_b_negative[Platelets]` | PASS |
| `test_compatibility` | `test_a_positive_request_never_gets_b_negative[RBC]` | PASS |
| `test_compatibility` | `test_a_positive_request_never_gets_b_negative[Whole Blood]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[A+-Plasma]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[A+-Platelets]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[A+-RBC]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[A+-Whole Blood]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[A--Plasma]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[A--Platelets]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[A--RBC]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[A--Whole Blood]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[AB+-Plasma]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[AB+-Platelets]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[AB+-RBC]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[AB+-Whole Blood]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[AB--Plasma]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[AB--Platelets]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[AB--RBC]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[AB--Whole Blood]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[B+-Plasma]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[B+-Platelets]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[B+-RBC]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[B+-Whole Blood]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[B--Plasma]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[B--Platelets]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[B--RBC]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[B--Whole Blood]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[O+-Plasma]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[O+-Platelets]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[O+-RBC]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[O+-Whole Blood]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[O--Plasma]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[O--Platelets]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[O--RBC]` | PASS |
| `test_compatibility` | `test_every_group_is_compatible_with_itself[O--Whole Blood]` | PASS |
| `test_compatibility` | `test_plasma_follows_reverse_abo_and_ignores_rh[A+-expected2]` | PASS |
| `test_compatibility` | `test_plasma_follows_reverse_abo_and_ignores_rh[AB+-expected0]` | PASS |
| `test_compatibility` | `test_plasma_follows_reverse_abo_and_ignores_rh[AB--expected1]` | PASS |
| `test_compatibility` | `test_plasma_follows_reverse_abo_and_ignores_rh[B--expected3]` | PASS |
| `test_compatibility` | `test_plasma_follows_reverse_abo_and_ignores_rh[O+-expected4]` | PASS |
| `test_compatibility` | `test_platelets_match_abo_and_protect_rh_negative_patients[A+-expected0]` | PASS |
| `test_compatibility` | `test_platelets_match_abo_and_protect_rh_negative_patients[A--expected1]` | PASS |
| `test_compatibility` | `test_platelets_match_abo_and_protect_rh_negative_patients[AB+-expected3]` | PASS |
| `test_compatibility` | `test_platelets_match_abo_and_protect_rh_negative_patients[O--expected2]` | PASS |
| `test_compatibility` | `test_rbc_follows_the_standard_table[A+-expected3]` | PASS |
| `test_compatibility` | `test_rbc_follows_the_standard_table[A--expected2]` | PASS |
| `test_compatibility` | `test_rbc_follows_the_standard_table[AB+-expected7]` | PASS |
| `test_compatibility` | `test_rbc_follows_the_standard_table[AB--expected6]` | PASS |
| `test_compatibility` | `test_rbc_follows_the_standard_table[B+-expected5]` | PASS |
| `test_compatibility` | `test_rbc_follows_the_standard_table[B--expected4]` | PASS |
| `test_compatibility` | `test_rbc_follows_the_standard_table[O+-expected1]` | PASS |
| `test_compatibility` | `test_rbc_follows_the_standard_table[O--expected0]` | PASS |
| `test_compatibility` | `test_rh_negative_patients_never_get_rh_positive_cells[A--Platelets]` | PASS |
| `test_compatibility` | `test_rh_negative_patients_never_get_rh_positive_cells[A--RBC]` | PASS |
| `test_compatibility` | `test_rh_negative_patients_never_get_rh_positive_cells[A--Whole Blood]` | PASS |
| `test_compatibility` | `test_rh_negative_patients_never_get_rh_positive_cells[AB--Platelets]` | PASS |
| `test_compatibility` | `test_rh_negative_patients_never_get_rh_positive_cells[AB--RBC]` | PASS |
| `test_compatibility` | `test_rh_negative_patients_never_get_rh_positive_cells[AB--Whole Blood]` | PASS |
| `test_compatibility` | `test_rh_negative_patients_never_get_rh_positive_cells[B--Platelets]` | PASS |
| `test_compatibility` | `test_rh_negative_patients_never_get_rh_positive_cells[B--RBC]` | PASS |
| `test_compatibility` | `test_rh_negative_patients_never_get_rh_positive_cells[B--Whole Blood]` | PASS |
| `test_compatibility` | `test_rh_negative_patients_never_get_rh_positive_cells[O--Platelets]` | PASS |
| `test_compatibility` | `test_rh_negative_patients_never_get_rh_positive_cells[O--RBC]` | PASS |
| `test_compatibility` | `test_rh_negative_patients_never_get_rh_positive_cells[O--Whole Blood]` | PASS |
| `test_compatibility` | `test_unknown_inputs_are_rejected` | PASS |
| `test_compatibility` | `test_whole_blood_needs_an_identical_group[A+]` | PASS |
| `test_compatibility` | `test_whole_blood_needs_an_identical_group[A-]` | PASS |
| `test_compatibility` | `test_whole_blood_needs_an_identical_group[AB+]` | PASS |
| `test_compatibility` | `test_whole_blood_needs_an_identical_group[AB-]` | PASS |
| `test_compatibility` | `test_whole_blood_needs_an_identical_group[B+]` | PASS |
| `test_compatibility` | `test_whole_blood_needs_an_identical_group[B-]` | PASS |
| `test_compatibility` | `test_whole_blood_needs_an_identical_group[O+]` | PASS |
| `test_compatibility` | `test_whole_blood_needs_an_identical_group[O-]` | PASS |
| `test_cross_match` | `test_a_unit_cannot_be_recorded_for_two_requests` | PASS |
| `test_cross_match` | `test_api_approve_allocates_units` | PASS |
| `test_cross_match` | `test_api_insufficient_stock_is_409_with_numbers` | PASS |
| `test_cross_match` | `test_api_matches_and_units_are_staff_only` | PASS |
| `test_cross_match` | `test_api_matches_preview` | PASS |
| `test_cross_match` | `test_approve_allocates_requested_number_of_units` | PASS |
| `test_cross_match` | `test_compatible_group_fills_the_gap_but_never_an_incompatible_one` | PASS |
| `test_cross_match` | `test_database_failure_releases_the_units` | PASS |
| `test_cross_match` | `test_exact_group_is_used_before_universal_donor` | PASS |
| `test_cross_match` | `test_insufficient_stock_changes_nothing` | PASS |
| `test_cross_match` | `test_losing_the_approval_race_releases_the_units` | PASS |
| `test_cross_match` | `test_preview_lists_units_without_reserving` | PASS |
| `test_cross_match` | `test_preview_only_for_pending_requests` | PASS |
| `test_cross_match` | `test_preview_reports_a_shortage` | PASS |
| `test_cross_match` | `test_reject_does_not_touch_inventory` | PASS |
| `test_cross_match` | `test_two_requests_never_share_a_unit` | PASS |
| `test_cross_match` | `test_units_taken_by_someone_else_are_reported` | PASS |
| `test_cross_match` | `test_units_that_do_not_fit_are_ignored[returned0-0]` | PASS |
| `test_cross_match` | `test_units_that_do_not_fit_are_ignored[returned1-0]` | PASS |
| `test_cross_match` | `test_units_that_do_not_fit_are_ignored[returned2-1]` | PASS |
| `test_donation_history` | `test_database_requires_positive_quantity` | PASS |
| `test_donation_history` | `test_donation_history_is_donor_specific` | PASS |
| `test_donation_history` | `test_donation_id_unique_in_database` | PASS |
| `test_donation_history` | `test_empty_history` | PASS |
| `test_donation_history` | `test_history_sorted_latest_first` | PASS |
| `test_donation_history` | `test_invalid_donation_rejected[kwargs0]` | PASS |
| `test_donation_history` | `test_invalid_donation_rejected[kwargs1]` | PASS |
| `test_donation_history` | `test_invalid_donation_rejected[kwargs2]` | PASS |
| `test_donation_history` | `test_invalid_donation_rejected[kwargs3]` | PASS |
| `test_donation_history` | `test_invalid_donation_rejected[kwargs4]` | PASS |
| `test_donation_history` | `test_invalid_donation_rejected[kwargs5]` | PASS |
| `test_donation_history` | `test_invalid_donor_id[-1]` | PASS |
| `test_donation_history` | `test_invalid_donor_id[0]` | PASS |
| `test_donation_history` | `test_invalid_donor_id[1]` | PASS |
| `test_donation_history` | `test_invalid_donor_id[None]` | PASS |
| `test_donation_history` | `test_invalid_donor_id[True]` | PASS |
| `test_donation_history` | `test_new_donation_saved_with_unique_id` | PASS |
| `test_donation_history` | `test_noncompleted_donation_is_visible_in_history` | PASS |
| `test_drives` | `test_created_drive_is_listed_with_slots` | PASS |
| `test_drives` | `test_donor_cannot_book_twice_for_one_drive` | PASS |
| `test_drives` | `test_drive_needs_at_least_one_slot` | PASS |
| `test_drives` | `test_full_slot_cannot_be_booked` | PASS |
| `test_drives` | `test_ineligible_donor_cannot_book` | PASS |
| `test_drives` | `test_invalid_slot_times_rejected[slot0]` | PASS |
| `test_drives` | `test_invalid_slot_times_rejected[slot1]` | PASS |
| `test_drives` | `test_reminder_sent_once_before_the_slot` | PASS |
| `test_drives` | `test_started_slot_cannot_be_booked` | PASS |
| `test_eligibility_check` | `test_55_days_since_last_donation_is_not_eligible` | PASS |
| `test_eligibility_check` | `test_age_limits_are_inclusive[dob0-True]` | PASS |
| `test_eligibility_check` | `test_age_limits_are_inclusive[dob1-False]` | PASS |
| `test_eligibility_check` | `test_age_limits_are_inclusive[dob2-True]` | PASS |
| `test_eligibility_check` | `test_age_limits_are_inclusive[dob3-True]` | PASS |
| `test_eligibility_check` | `test_age_limits_are_inclusive[dob4-False]` | PASS |
| `test_eligibility_check` | `test_age_limits_are_inclusive[dob5-True]` | PASS |
| `test_eligibility_check` | `test_calculate_age_counts_birthday_on_the_day` | PASS |
| `test_eligibility_check` | `test_deferred_or_cancelled_donation_does_not_start_the_wait[CANCELLED]` | PASS |
| `test_eligibility_check` | `test_deferred_or_cancelled_donation_does_not_start_the_wait[DEFERRED]` | PASS |
| `test_eligibility_check` | `test_donated_today_must_wait_the_full_period` | PASS |
| `test_eligibility_check` | `test_donor_with_no_history_is_eligible` | PASS |
| `test_eligibility_check` | `test_eligible_donor_has_no_reasons` | PASS |
| `test_eligibility_check` | `test_every_failed_rule_is_reported` | PASS |
| `test_eligibility_check` | `test_exactly_56_days_since_last_donation_is_eligible` | PASS |
| `test_eligibility_check` | `test_invalid_date_of_birth_raises[1990-01-01]` | PASS |
| `test_eligibility_check` | `test_invalid_date_of_birth_raises[None]` | PASS |
| `test_eligibility_check` | `test_invalid_date_of_birth_raises[dob2]` | PASS |
| `test_eligibility_check` | `test_invalid_donor_id_raises[-1]` | PASS |
| `test_eligibility_check` | `test_invalid_donor_id_raises[0]` | PASS |
| `test_eligibility_check` | `test_invalid_donor_id_raises[1]` | PASS |
| `test_eligibility_check` | `test_invalid_donor_id_raises[None]` | PASS |
| `test_eligibility_check` | `test_invalid_donor_id_raises[True]` | PASS |
| `test_eligibility_check` | `test_invalid_last_donation_date_raises[2026-01-01]` | PASS |
| `test_eligibility_check` | `test_invalid_last_donation_date_raises[last1]` | PASS |
| `test_eligibility_check` | `test_invalid_weight_raises[-5]` | PASS |
| `test_eligibility_check` | `test_invalid_weight_raises[0]` | PASS |
| `test_eligibility_check` | `test_invalid_weight_raises[60]` | PASS |
| `test_eligibility_check` | `test_invalid_weight_raises[None]` | PASS |
| `test_eligibility_check` | `test_invalid_weight_raises[True]` | PASS |
| `test_eligibility_check` | `test_invalid_weight_raises[inf]` | PASS |
| `test_eligibility_check` | `test_invalid_weight_raises[nan]` | PASS |
| `test_eligibility_check` | `test_minimum_weight_is_45_kg[120-True]` | PASS |
| `test_eligibility_check` | `test_minimum_weight_is_45_kg[44-False]` | PASS |
| `test_eligibility_check` | `test_minimum_weight_is_45_kg[44.9-False]` | PASS |
| `test_eligibility_check` | `test_minimum_weight_is_45_kg[45-True]` | PASS |
| `test_eligibility_check` | `test_minimum_weight_is_45_kg[45.0-True]` | PASS |
| `test_eligibility_check` | `test_most_recent_completed_donation_is_the_one_that_counts` | PASS |
| `test_eligibility_check` | `test_never_donated_before_is_fine` | PASS |
| `test_eligibility_check` | `test_only_the_donors_own_history_counts` | PASS |
| `test_eligibility_check` | `test_recent_completed_donation_blocks_donor` | PASS |
| `test_eligibility_check` | `test_today_defaults_to_the_real_date` | PASS |
| `test_emergency_callout` | `test_trigger_emergency_callout_dispatches_notifications` | PASS |
| `test_emergency_callout` | `test_trigger_emergency_callout_returns_dict` | PASS |
| `test_inventory_blood12` | `test_duplicate_id_rejected_by_database` | PASS |
| `test_inventory_blood12` | `test_future_collection_date_rejected` | PASS |
| `test_inventory_blood12` | `test_invalid_input_rejected[A+-Unknown]` | PASS |
| `test_inventory_blood12` | `test_invalid_input_rejected[X+-RBC]` | PASS |
| `test_inventory_blood12` | `test_new_bag_gets_unique_id` | PASS |
| `test_inventory_blood12` | `test_saved_bag_can_be_found` | PASS |
| `test_inventory_blood13` | `test_calculate_component_expiry[Plasma-365]` | PASS |
| `test_inventory_blood13` | `test_calculate_component_expiry[Platelets-5]` | PASS |
| `test_inventory_blood13` | `test_calculate_component_expiry[RBC-42]` | PASS |
| `test_inventory_blood13` | `test_calculate_component_expiry[Whole Blood-35]` | PASS |
| `test_inventory_blood13` | `test_future_collection_date_rejected` | PASS |
| `test_inventory_blood13` | `test_invalid_bag_does_not_save` | PASS |
| `test_inventory_blood13` | `test_invalid_collection_date_rejected[2026-01-01]` | PASS |
| `test_inventory_blood13` | `test_invalid_collection_date_rejected[None]` | PASS |
| `test_inventory_blood13` | `test_invalid_collection_date_rejected[collected1]` | PASS |
| `test_inventory_blood13` | `test_saved_bag_has_expiry_date[Plasma]` | PASS |
| `test_inventory_blood13` | `test_saved_bag_has_expiry_date[Platelets]` | PASS |
| `test_inventory_blood13` | `test_saved_bag_has_expiry_date[RBC]` | PASS |
| `test_inventory_blood13` | `test_saved_bag_has_expiry_date[Whole Blood]` | PASS |
| `test_inventory_blood13` | `test_unknown_component_rejected` | PASS |
| `test_inventory_blood14` | `test_automatic_expiry_writes_audit` | PASS |
| `test_inventory_blood14` | `test_available_bags_exclude_allocated` | PASS |
| `test_inventory_blood14` | `test_expired_at_creation` | PASS |
| `test_inventory_blood14` | `test_expiry_boundary_excluded_without_scheduler` | PASS |
| `test_inventory_blood14` | `test_fresh_bag_available` | PASS |
| `test_inventory_blood14` | `test_invalid_actor_rejected[-1]` | PASS |
| `test_inventory_blood14` | `test_invalid_actor_rejected[0]` | PASS |
| `test_inventory_blood14` | `test_invalid_actor_rejected[None]` | PASS |
| `test_inventory_blood14` | `test_invalid_actor_rejected[True]` | PASS |
| `test_inventory_blood14` | `test_invalid_actor_rejected[user]` | PASS |
| `test_inventory_blood14` | `test_only_expired_available_bags_change` | PASS |
| `test_inventory_blood14` | `test_repeated_expiry_does_not_duplicate_audit` | PASS |
| `test_inventory_cross_match` | `test_allocate_is_all_or_nothing` | PASS |
| `test_inventory_cross_match` | `test_dispatch_marks_units_and_is_safe_to_retry` | PASS |
| `test_inventory_cross_match` | `test_expired_allocated_unit_cannot_be_dispatched` | PASS |
| `test_inventory_cross_match` | `test_find_prefers_exact_group_then_soonest_expiry` | PASS |
| `test_inventory_cross_match` | `test_find_respects_quantity_and_skips_expired` | PASS |
| `test_inventory_cross_match` | `test_only_one_of_two_competing_allocations_wins` | PASS |
| `test_inventory_cross_match` | `test_release_only_touches_the_owning_request` | PASS |
| `test_low_stock` | `test_allocated_not_counted` | PASS |
| `test_low_stock` | `test_dispatched_not_counted` | PASS |
| `test_low_stock` | `test_empty_stock_reports_zero` | PASS |
| `test_low_stock` | `test_expired_not_counted` | PASS |
| `test_low_stock` | `test_groups_and_components_separated` | PASS |
| `test_low_stock` | `test_invalid_threshold_rejected[-1]` | PASS |
| `test_low_stock` | `test_invalid_threshold_rejected[1.5]` | PASS |
| `test_low_stock` | `test_invalid_threshold_rejected[5]` | PASS |
| `test_low_stock` | `test_invalid_threshold_rejected[None]` | PASS |
| `test_low_stock` | `test_invalid_threshold_rejected[True]` | PASS |
| `test_low_stock` | `test_one_available_bag_is_low` | PASS |
| `test_low_stock` | `test_threshold_boundary` | PASS |
| `test_record_donation` | `test_completed_donation_is_saved_and_added_to_stock` | PASS |
| `test_record_donation` | `test_decimal_weight_is_accepted` | PASS |
| `test_record_donation` | `test_deferred_donation_skips_eligibility_and_stock` | PASS |
| `test_record_donation` | `test_eligibility_needs_a_profile` | PASS |
| `test_record_donation` | `test_eligibility_uses_the_saved_profile` | PASS |
| `test_record_donation` | `test_ineligible_donor_cannot_donate_again_within_56_days` | PASS |
| `test_record_donation` | `test_invalid_donation_date_rejected[2026-01-01]` | PASS |
| `test_record_donation` | `test_invalid_donation_date_rejected[None]` | PASS |
| `test_record_donation` | `test_invalid_donation_date_rejected[bad_date0]` | PASS |
| `test_submit_blood_request` | `test_api_bad_body_returns_422` | PASS |
| `test_submit_blood_request` | `test_api_other_hospitals_request_is_404` | PASS |
| `test_submit_blood_request` | `test_api_requires_hospital_role` | PASS |
| `test_submit_blood_request` | `test_api_rule_error_returns_422` | PASS |
| `test_submit_blood_request` | `test_api_submit_returns_201_and_pending` | PASS |
| `test_submit_blood_request` | `test_get_missing_request_raises` | PASS |
| `test_submit_blood_request` | `test_hospital_only_sees_own_requests` | PASS |
| `test_submit_blood_request` | `test_quantity_above_limit_rejected` | PASS |
| `test_submit_blood_request` | `test_quantity_at_limit_accepted` | PASS |
| `test_submit_blood_request` | `test_required_by_in_future_accepted` | PASS |
| `test_submit_blood_request` | `test_required_by_in_past_rejected` | PASS |
| `test_submit_blood_request` | `test_schema_rejects_bad_field[blood_group-C+]` | PASS |
| `test_submit_blood_request` | `test_schema_rejects_bad_field[blood_group-None]` | PASS |
| `test_submit_blood_request` | `test_schema_rejects_bad_field[component-Water]` | PASS |
| `test_submit_blood_request` | `test_schema_rejects_bad_field[notes-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx]` | PASS |
| `test_submit_blood_request` | `test_schema_rejects_bad_field[patient_reference-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx]` | PASS |
| `test_submit_blood_request` | `test_schema_rejects_bad_field[quantity--1]` | PASS |
| `test_submit_blood_request` | `test_schema_rejects_bad_field[quantity-0]` | PASS |
| `test_submit_blood_request` | `test_schema_rejects_bad_field[quantity-2.5]` | PASS |
| `test_submit_blood_request` | `test_schema_rejects_bad_field[quantity-3]` | PASS |
| `test_submit_blood_request` | `test_schema_rejects_bad_field[quantity-True]` | PASS |
| `test_submit_blood_request` | `test_schema_rejects_bad_field[required_by-not-a-date]` | PASS |
| `test_submit_blood_request` | `test_schema_rejects_bad_field[urgency-asap]` | PASS |
| `test_submit_blood_request` | `test_schema_rejects_unknown_fields` | PASS |
| `test_submit_blood_request` | `test_schema_reports_all_errors_and_defaults` | PASS |
| `test_submit_blood_request` | `test_schema_trims_and_blanks_text_fields` | PASS |
| `test_submit_blood_request` | `test_submit_valid_request_is_pending` | PASS |

## Appendix B. Every integration test

| Test file | Test | Result |
|---|---|---|
| `test_account_lockout` | `test_failed_attempt_after_lock_expires_starts_new_count` | PASS |
| `test_account_lockout` | `test_fifth_wrong_password_locks_for_thirty_minutes` | PASS |
| `test_account_lockout` | `test_http_login_rejects_correct_password_after_five_failures` | PASS |
| `test_account_lockout` | `test_successful_login_resets_consecutive_failures` | PASS |
| `test_admin_accounts_api` | `test_admin_creates_accounts_that_can_log_in_with_their_role` | PASS |
| `test_admin_accounts_api` | `test_email_is_normalised_and_must_be_unique` | PASS |
| `test_admin_accounts_api` | `test_only_admins_create_accounts` | PASS |
| `test_admin_accounts_api` | `test_role_and_hospital_rules` | PASS |
| `test_auth_api` | `test_each_role_logs_in_and_sees_its_own_identity[admin]` | PASS |
| `test_auth_api` | `test_each_role_logs_in_and_sees_its_own_identity[blood_bank_staff]` | PASS |
| `test_auth_api` | `test_each_role_logs_in_and_sees_its_own_identity[donor]` | PASS |
| `test_auth_api` | `test_each_role_logs_in_and_sees_its_own_identity[hospital_rep]` | PASS |
| `test_auth_api` | `test_login_rejects_invalid_or_unverified_accounts[donor@example.com-wrong-password]` | PASS |
| `test_auth_api` | `test_login_rejects_invalid_or_unverified_accounts[missing@example.com-ExamplePassword123!]` | PASS |
| `test_auth_api` | `test_login_rejects_invalid_or_unverified_accounts[unverified@example.com-ExamplePassword123!]` | PASS |
| `test_auth_api` | `test_logout_revokes_session` | PASS |
| `test_auth_api` | `test_missing_or_fabricated_token_cannot_access_identity` | PASS |
| `test_auth_api` | `test_staff_and_admin_routes_enforce_roles` | PASS |
| `test_dashboard_actions_api` | `test_admin_sends_reminders_for_slots_starting_soon` | PASS |
| `test_dashboard_actions_api` | `test_bags_collected_in_the_future_are_refused` | PASS |
| `test_dashboard_actions_api` | `test_donor_booking_shows_up_for_staff_and_admin` | PASS |
| `test_dashboard_actions_api` | `test_donor_gets_one_slot_per_drive` | PASS |
| `test_dashboard_actions_api` | `test_donor_without_profile_is_told_why_booking_failed` | PASS |
| `test_dashboard_actions_api` | `test_drive_form_rules_are_enforced` | PASS |
| `test_dashboard_actions_api` | `test_drive_scheduled_by_staff_or_admin_is_visible_to_every_viewer` | PASS |
| `test_dashboard_actions_api` | `test_expiry_check_from_the_dashboard` | PASS |
| `test_dashboard_actions_api` | `test_full_slot_cannot_be_booked` | PASS |
| `test_dashboard_actions_api` | `test_logging_a_batch_of_bags_adds_each_one_to_stock` | PASS |
| `test_dashboard_actions_api` | `test_only_coordinators_can_schedule_drives` | PASS |
| `test_dashboard_actions_api` | `test_only_donors_can_book` | PASS |
| `test_dashboard_actions_api` | `test_rejected_request_leaves_the_queue_and_hospital_sees_it` | PASS |
| `test_dashboard_actions_api` | `test_request_form_validation` | PASS |
| `test_dashboard_actions_api` | `test_request_from_the_form_reaches_the_staff_queue` | PASS |
| `test_dashboard_actions_api` | `test_request_moves_between_the_staff_tables` | PASS |
| `test_demo_seed` | `test_admin_dashboard_loads` | PASS |
| `test_demo_seed` | `test_donor_dashboard_has_profile_history_and_drives` | PASS |
| `test_demo_seed` | `test_hospital_dashboard_lists_its_requests` | PASS |
| `test_demo_seed` | `test_seed_demo_twice_adds_nothing` | PASS |
| `test_demo_seed` | `test_staff_dashboard_has_stock_requests_and_drives` | PASS |
| `test_donor_profile_api` | `test_donor_creates_and_reads_only_own_profile` | PASS |
| `test_donor_profile_api` | `test_required_fields_and_duplicate_profile` | PASS |
| `test_donor_profile_api` | `test_staff_and_unauthenticated_callers_are_denied` | PASS |
| `test_emergency_callout_api` | `test_emergency_callout_invalid_input` | PASS |
| `test_emergency_callout_api` | `test_emergency_callout_rbac_restriction` | PASS |
| `test_emergency_callout_api` | `test_emergency_callout_success` | PASS |
| `test_low_stock_api` | `test_hospital_cannot_view_alerts` | PASS |
| `test_low_stock_api` | `test_invalid_threshold_returns_422` | PASS |
| `test_low_stock_api` | `test_staff_can_get_low_stock_alerts` | PASS |
| `test_request_dispatch_flow` | `test_a_unit_is_never_allocated_to_two_requests` | PASS |
| `test_request_dispatch_flow` | `test_approve_with_insufficient_stock_is_refused` | PASS |
| `test_request_dispatch_flow` | `test_dispatch_requires_approval_first` | PASS |
| `test_request_dispatch_flow` | `test_health_endpoint` | PASS |
| `test_request_dispatch_flow` | `test_incompatible_and_expired_units_are_not_matched` | PASS |
| `test_request_dispatch_flow` | `test_roles_are_enforced_across_modules` | PASS |
| `test_request_dispatch_flow` | `test_submit_approve_dispatch_moves_units_through_inventory` | PASS |
| `test_signup_api` | `test_duplicate_signup_and_early_resend_are_rejected` | PASS |
| `test_signup_api` | `test_public_signup_cannot_choose_a_privileged_role` | PASS |
| `test_signup_api` | `test_signup_requires_correct_otp_before_login` | PASS |
| `test_signup_rules` | `test_delivery_failure_does_not_create_account` | PASS |
| `test_signup_rules` | `test_expired_code_can_be_replaced_and_old_code_fails` | PASS |
| `test_signup_rules` | `test_five_wrong_codes_block_verification` | PASS |
