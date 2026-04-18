### CRON and trading flow improvement

#### General PLAN
05.00 Is the L0, L1, L2 Process. Can take much as needed time!
1. Keep this! HOME/workspace/runtime/cron/trader_morning_prep.sh
2. Wrap trader_morning_prep.sh under skill /trader:screening so the cron trigger the claude code. Not the static script.
##### CRON Trader Intraday
HOME/workspace/runtime/cron/trader_intraday_10m.sh
1. unnecessary to be exits every 10 minutes. We can merge it with HOME/workspace/runtime/cron/trader_morning_prep.sh on the 05.00 runtime. I saw it does the L2 right? The logic under this code is good, so keep it but under the L2 process schedule. It will be under skill /trader:screening part too following the General PLAN.
2. trader_intraday_10m.sh logic is off, because it only take up to 8. This filter limit our opportunity!

trader_summary_30m.sh
