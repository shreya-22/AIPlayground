import sys
sys.path.insert(0, '.')
from config import settings; settings._config_instance = None
from config.settings import get_config
from services.sql_service import get_data_source
from services.productivity_service import ProductivityService
from services.billing_service import BillingService
from services.activity_tracking_service import ActivityTrackingService
from services.case_service import CaseService

config = get_config()
ds = get_data_source(config)

# Productivity
prod = ProductivityService(ds)
recs = prod.get_productivity(start_date='2026-03-01', end_date='2026-03-12')
print(f'Productivity records (Mar 2026): {len(recs)}')
print(f'  Sample: {recs[0].case_manager} | {recs[0].report_date} | TCM={recs[0].tcm_count}')

# Billing
cs = CaseService(ds)
cases = cs.get_case_list()
bill = BillingService()
summaries = bill.compute_all(cases)
print(f'Billing summaries: {len(summaries)}')
for s in summaries[:3]:
    print(f'  {s.member_name}: {s.case_age_days}d | tier={s.billing_tier} | total=${s.total_billed}')
approaching = bill.get_approaching_tier_change(summaries)
print(f'Approaching tier change: {len(approaching)}')
rates = bill.get_rates()
print(f'Rates loaded: {rates}')

# Activity
act = ActivityTrackingService(ds)
summary = act.get_last_24h_summary()
print(f'Last-24h: journal={summary.journal_entries}, progress={summary.progress_notes}, referrals={summary.new_referrals}, simulated={summary.is_simulated}')
refs = act.get_all_referrals()
print(f'All referrals: {len(refs)}')
monthly = act.get_monthly_referral_counts(months=6)
print(f'Monthly referral counts: {monthly}')

print('\nAll validations passed.')
