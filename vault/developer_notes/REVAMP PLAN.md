Current implementation is dirty, unclear, confusing. MAKE A MAJOR CHANGES. Archive all the CRON command! Make a copy of skills, tools, playbooks, commands, in case we broke something, VERY IMPORTANT.

## Main Objects: current_trade
#### Stock status:
* Filtered List: just a general list we might interested at, so we don't need to scan all 900 tickers.
* Watchlist: List of good stocks, entering to any of this list have more chance to grow because they have a good narrative, or have any good signal, without redflag  
* Superlist: We are monitoring for good entry, good setup, and our must have top holding right now. We need to immediate entry or looking for the nearest entry.
* Exitlist: Time to exit from superlist, might be still on watchlist.

*all the list above is in the form of array of object {ticker:XXXX, confidence:XX, current_plan: {buy_at_price/wait_bid_offer} details:....}

#### Trader status
* Regime (Market)
* Aggressiveness based on portfolio:
* Interesting Sector(s) - Array of sectors
* Interesting news/narrative - array of objects(ticker, news content, source, confident score)
* Balance
* Profit / Loss
* Holdings

## P00 - General Plan
Build multi layer skills.
All output should enrich the current_trade object.

| Process Name                                | Objective                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Output                                                                                                                                                                                                                    | Skill Name                                                                            | When To Run                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| L0: Portfolio Analysis                      | Evaluate our performance                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | 1. Current holding and cash<br>2. Trader status: insight, how balance is our holding, how much risk we have.                                                                                                              | /trade:portfolio                                                                      | 1. CRON 03.00 AM                                                                                                                                                                                                                                                                                                               |
| L1: Knowledge Context and Insight Gathering | 1. Run through all insight we've got on L1-A and L1-B though API backend local<br>2. Connecting the dots! AI analysis.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | 1. Good narative or insight<br>2. Generate Watchlist<br><br>Send recap to telegram, whats the interesing news, insight, how much ticker, what sectors.                                                                    | /trade:insight                                                                        | 1. CRON 04.00 AM with "claude ..." command to call the skill and execute<br>2. skill /trade:insight trigger and start                                                                                                                                                                                                          |
| L1-A : Helper, CRON, Telegram Listening     | Get insight to insight db from telegram                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Insight chunk on db                                                                                                                                                                                                       | 1. API RAG for asking question<br>2. RAG Top Ticker for getting top confidence ticker | Every 30 minutes                                                                                                                                                                                                                                                                                                               |
| L1-B : Helper, CRON, Thread Listening       | Get insight to insight db from thrads                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | insight chink on db                                                                                                                                                                                                       | 1. API RAG for asking question<br>2. RAG Top Ticker for getting top confidence ticker | Every 6 hours                                                                                                                                                                                                                                                                                                                  |
| L2: Screening                               | Get best of the watchlist. Analysis for<br>1. Price volume analysis, wyckoff, spring, HH, HL.<br>2. Broker analysis, accumulation? A lot of retail? Bandar average? SID Analysis<br>3. Transaction analysis and Bid offer analysis from yesterday if any (get yesterday record or pull yesterday data from stockbit)<br>4. Narrative analysis<br><br>Each of the point have "redflag/weak/strong/superstrong".<br><br>1 superstrong = GO for superlist<br>3 strong = GO for superlist<br>2 strong without redflag = GO for superlist<br><br>Analyze with AI, not rule based code. Each of ticker 1 AI analysis!<br><br>Hints, make sure our holding is part of the screening! If any 2 redflag, think if we need to exit. Send to L4 and L5 | Superlist: buy_at_price/sell_at_price/wait_bid_offer<br><br>buy_at_price / sell_at_price --> go to tradeplan and execute<br><br>wait_bid_offer --> wait for monitoring<br><br>Send notification superlist to telegram the | /trade:screening                                                                      | CRON 05.00 call /trade:screening start with "claude --settings .claude/settings.openclaude.json" to trigger the python running and each ticker screening.                                                                                                                                                                      |
| L3: Monitoring                              | Read from current_trader.superlist where ticker is wait_bid_offer.  We want a sniper entry. Best entry we can have.<br>Bid offer analysis, transaction analysis. (make a placeholder, will give you the detail later to add on playbook and skills).<br><br>* Playbook and skills --> for every 30 minutes AI analysis<br>* Tools = from realtime signal listener and 10 minutes cron. We will make a very accurate code here to generate best snapshot and entry signal.<br>- High confidence snapshot = BUY Immediately<br>- Medium to low confidence = Wait for AI to combine in every 30 minutes.                                                                                                                                       | Entry signal! If found, go to tradeplan and execute!<br><br>Sent to telegram if found entry signal                                                                                                                        | #NA                                                                                   | 1. Code realtime (from realtime websocket stockbit) that then pass our python. Python will know the signal and send it directly to L4.<br>2. CRON every 10 minutes as backup (market time)<br>3. CRON every 30 minutes to see whats going on past 30 minutes. Use AI analysis here! See the interesting snapshot (market time) |
| L4: Tradeplan                               | Simple, make a good trade plan based on current_trade L0 result. Triggered by L2 buy_at_price or L3 entry signal.<br><br>AI Analysis!                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Bid/Offer/Cutloss/TP/Trailing Stop<br>Go to L5.                                                                                                                                                                           | /trader:tradeplan                                                                     | Signal from L2 and L3.<br><br>Do "claude ......" to think the tradeplan                                                                                                                                                                                                                                                        |
| L5: Execute                                 | Hit stockbit API with correct param, lot sizing, make sure no error.<br><br>Option: Insert Buy, Insert Sell, Set cut loss, insert TP, trailing stop (I will add more stockbit API)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Send the order.<br>CRON for every 30 minutes if success.<br>Send to telegram. Update the holding when success.                                                                                                            | /trader:execute                                                                       | 1. Realtime entry<br>2. CRON every 30 minutes to monitor success/not                                                                                                                                                                                                                                                           |

#### Rule!
1. In managing current_trade, can also store to backend golang if needed.


## Trading Guide
#### [P1] Screening
Just learn from the current screening skills and tools. I will review later.
* how to interact with RAG and threads insight
* stockbit screener tools
	* screener beneran
	* yesterday transaction
#### [P2] Bid Offer Analysis

[placeholder, explore dulu bareng claude, brainstorm]


* tiap 10 menit sekali:
	* Thick offer wall buy signal
		* cek ada thick offer wall, tapi buying done lumayan kuat? Ini udah strong signal
		* hit API transaksi apakah ada tembok offer yang di withdraw (bisa liat di stockbit) ini tambah strong signal
	* Support breakdown broker buy
		* cek apakah turun dari support tapi ada masive buying dari broker (freq kecil, lot besar)
	* Breakout powerful
		* cek apakah resist di breakout, diiringi dengan offer yang selalu "dibeli" oleh buyer.
	* Cek narative RAG v3 dari telegram/threads, kalau ada sinyal menarik.

Bid Offer thick wall setup:

```
def analyze_near_book(bids: list, offers: list, n: int = 7) -> dict:
    # bids sorted desc by price (nearest first)
    # offers sorted asc by price (nearest first)
    bids_near   = sorted(bids,   key=lambda x: x["price"], reverse=True)[:n]
    offers_near = sorted(offers, key=lambda x: x["price"])[:n]

    ratios = []
    for i, (b, o) in enumerate(zip(bids_near, offers_near)):
        ratios.append({
            "level": i + 1,
            "ratio": round(o["lot"] / b["lot"], 2) if b["lot"] else 999,
            "bid_lot": b["lot"],
            "offer_lot": o["lot"],
        })

    r = [x["ratio"] for x in ratios]

    # spike: level 1 dominates and is 2x+ any other level
    is_spike = r[0] >= 3.0 and r[0] >= 2.0 * max(r[1:])

    # gradient: ratios trend upward level by level
    rising = sum(1 for i in range(len(r)-1) if r[i+1] > r[i])
    is_gradient = rising >= len(r) * 0.6

    # bid thinness: are top 3 bid lots much smaller than levels 4-7?
    near_bid_avg = sum(x["bid_lot"] for x in ratios[:3]) / 3
    far_bid_avg  = sum(x["bid_lot"] for x in ratios[3:]) / max(len(ratios[3:]), 1)
    retail_scared = near_bid_avg < far_bid_avg * 0.7

    pattern = "spike" if is_spike else "gradient" if is_gradient else "normal"

    return {
        "pattern": pattern,
        "retail_scared": retail_scared,
        "ratios": r,
        "level_1_ratio": r[0],
    }
```

Retail avoider (For screening layer):
```
fetch("https://exodus.stockbit.com/order-trade/broker/activity?broker_code=XL&broker_code=YP&broker_code=XC&broker_code=PD&limit=50&page=1&from=2026-04-17&to=2026-04-17&transaction_type=TRANSACTION_TYPE_NET&market_board=MARKET_TYPE_REGULER&investor_type=INVESTOR_TYPE_ALL", {
  "headers": {
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9",
    "authorization": "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6ImExNWQ5OGE2LTdkYzgtNDM3NS05NDk0LTEyOWJlM2RlODVkNCIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7InVzZSI6Im9qaW4iLCJlbWEiOiJvamluY2FzaEBnbWFpbC5jb20iLCJmdWwiOiJGYXV6YW4gUmFtYWRoYW4iLCJzZXMiOiJUMWJQNUdCTk1KRHgzV3JqIiwiZHZjIjoiNzlhYWNmOGFkZmY5MDM4YzQzMWExMDRkYTY0ZjdiNDciLCJ1aWQiOjYzODU2MSwiY291IjoiSUQifSwiZXhwIjoxNzc2NjE1MTk0LCJpYXQiOjE3NzY1Mjg3OTQsImlzcyI6IlNUT0NLQklUIiwianRpIjoiMTkzZGE2ZGQtZWQwMy00OTA2LWI4NGItODc1YzAwZTkyMjZjIiwibmJmIjoxNzc2NTI4Nzk0LCJ2ZXIiOiJ2MSJ9.PKhXDzsEJCwhR3KUGzoFGnA7i64Ce9_qi7lqboBU_DrF1dcSgfGBx1pCw0sK0UBL9jvoM03FsbV2RAQwdiWETuGZUTm6JXoIAScX9LFD4zyUiwAZDmAPGGrN3Op7w48uvYYJ4BNteARXEZ9eTsJl9PwLbC8EYuuLBeVia_TjYFB31p58ieYAzewbC_FNiJxt0VCSW_h5-3PWul7OqmR5VnfKsiKuC3LudKIjrwNJFA1Tas3g39ErIaSzz3LESbyzN7jJuKxl0NbhJLuFY_bzlrf7-DdXoeXQzrjSvZeyufLpOo_Jk7Lh6wbtg_duxe1-9UMAGCIauVcOVrGFooeA7Q",
    "sec-ch-ua": "\"Chromium\";v=\"116\", \"Not)A;Brand\";v=\"24\", \"Google Chrome\";v=\"116\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site"
  },
  "referrer": "https://stockbit.com/",
  "referrerPolicy": "strict-origin-when-cross-origin",
  "body": null,
  "method": "GET",
  "mode": "cors",
  "credentials": "include"
});

{
    "message": "Successfully loaded Broker Activity data",
    "data": {
        "broker_activity_transaction": {
            "brokers_buy": [
                {
                    "stock_code": "BBCA",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": 230751955000,
                    "lot": 357391,
                    "avg_price": 6461.327949264119,
                    "freq": 29386,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/BBCA.png",
                        "corpaction": {
                            "active": false,
                            "icon": "",
                            "text": ""
                        },
                        "notation": []
                    },
                    "nval_trend": []
                },
                {
                    "stock_code": "BMRI",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": 85281074000,
                    "lot": 184978,
                    "avg_price": 4619.789943459222,
                    "freq": 9784,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/BMRI.png",
                        "corpaction": {
                            "active": false,
                            "icon": "https://assets.stockbit.com/images/corp_action_event_icon.svg",
                            "text": "Perusahaan Memiliki Corporate Action"
                        },
                        "notation": []
                    },
                    "nval_trend": []
                },
                {
                    "stock_code": "HMSP",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": 1563889000,
                    "lot": 20812,
                    "avg_price": 751.1595394736842,
                    "freq": 593,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/HMSP.png",
                        "corpaction": {
                            "active": false,
                            "icon": "https://assets.stockbit.com/images/corp_action_event_icon.svg",
                            "text": "Perusahaan Memiliki Corporate Action"
                        },
                        "notation": []
                    },
                    "nval_trend": []
                }
            ],
            "brokers_sell": [
                {
                    "stock_code": "ADRO",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": -42255450000,
                    "lot": -165829,
                    "avg_price": 2547.487418102082,
                    "freq": 8899,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/ADRO.png?version=1753857016610110434",
                        "corpaction": {
                            "active": false,
                            "icon": "",
                            "text": ""
                        },
                        "notation": []
                    },
                    "nval_trend": []
                },
                {
                    "stock_code": "AADI",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": -41851597500,
                    "lot": -37117,
                    "avg_price": 11270.125325782683,
                    "freq": 4093,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/AADI.png?version=1731380937972873322",
                        "corpaction": {
                            "active": false,
                            "icon": "https://assets.stockbit.com/images/corp_action_event_icon.svg",
                            "text": "Perusahaan Memiliki Corporate Action"
                        },
                        "notation": []
                    },
                    "nval_trend": []
                },
                {
                    "stock_code": "EMAS",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": -34893832500,
                    "lot": -40630,
                    "avg_price": 8556.229513046565,
                    "freq": 5453,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/EMAS.png?version=1757313721556982559",
                        "corpaction": {
                            "active": true,
                            "icon": "https://assets.stockbit.com/images/corp_action_event_icon.svg",
                            "text": "Perusahaan Memiliki Corporate Action"
                        },
                        "notation": []
                    },
                    "nval_trend": []
                },
                {
                    "stock_code": "BRMS",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": -31461134000,
                    "lot": -362747,
                    "avg_price": 866.5165423331205,
                    "freq": 8795,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/BRMS.png",
                        "corpaction": {
                            "active": false,
                            "icon": "https://assets.stockbit.com/images/corp_action_event_icon.svg",
                            "text": "Perusahaan Memiliki Corporate Action"
                        },
                        "notation": []
                    },
                    "nval_trend": []
                },
                {
                    "stock_code": "BREN",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": -28912117500,
                    "lot": -44253,
                    "avg_price": 6509.00546849494,
                    "freq": 2268,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/BREN.png",
                        "corpaction": {
                            "active": false,
                            "icon": "https://assets.stockbit.com/images/corp_action_event_icon.svg",
                            "text": "Perusahaan Memiliki Corporate Action"
                        },
                        "notation": []
                    },
                    "nval_trend": []
                },
                {
                    "stock_code": "CUAN",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": -26231563000,
                    "lot": -168170,
                    "avg_price": 1578.2418594706219,
                    "freq": 14946,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/CUAN.png",
                        "corpaction": {
                            "active": false,
                            "icon": "https://assets.stockbit.com/images/corp_action_event_icon.svg",
                            "text": "Perusahaan Memiliki Corporate Action"
                        },
                        "notation": []
                    },
                    "nval_trend": []
                },
                {
                    "stock_code": "BIPI",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": -5603208400,
                    "lot": -204891,
                    "avg_price": 282.5167160763156,
                    "freq": 16635,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/BIPI.png",
                        "corpaction": {
                            "active": false,
                            "icon": "https://assets.stockbit.com/images/corp_action_event_icon.svg",
                            "text": "Perusahaan Memiliki Corporate Action"
                        },
                        "notation": [
                            {
                                "notation_code": "L",
                                "notation_desc": "Perusahaan Tercatat belum menyampaikan laporan keuangan",
                                "icon_url": {
                                    "light_mode": "https://assets.stockbit.com/logos/notations/light/L.png",
                                    "dark_mode": "https://assets.stockbit.com/logos/notations/dark/L.png"
                                }
                            }
                        ]
                    },
                    "nval_trend": []
                },
                {
                    "stock_code": "ACES",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": -5555713400,
                    "lot": -146934,
                    "avg_price": 377.51375504573093,
                    "freq": 5855,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/ACES-NEW.png",
                        "corpaction": {
                            "active": false,
                            "icon": "https://assets.stockbit.com/images/corp_action_event_icon.svg",
                            "text": "Perusahaan Memiliki Corporate Action"
                        },
                        "notation": []
                    },
                    "nval_trend": []
                },
                {
                    "stock_code": "WIFI",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": -5310889000,
                    "lot": -21238,
                    "avg_price": 2490.76794684556,
                    "freq": 3624,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/WIFI.png",
                        "corpaction": {
                            "active": false,
                            "icon": "https://assets.stockbit.com/images/corp_action_event_icon.svg",
                            "text": "Perusahaan Memiliki Corporate Action"
                        },
                        "notation": []
                    },
                    "nval_trend": []
                },
                {
                    "stock_code": "LSIP",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": -5204446000,
                    "lot": -32149,
                    "avg_price": 1620.1989238148572,
                    "freq": 1045,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/LSIP.png",
                        "corpaction": {
                            "active": false,
                            "icon": "https://assets.stockbit.com/images/corp_action_event_icon.svg",
                            "text": "Perusahaan Memiliki Corporate Action"
                        },
                        "notation": []
                    },
                    "nval_trend": []
                },
                {
                    "stock_code": "PADI",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": -5143695400,
                    "lot": -431804,
                    "avg_price": 124.14110070920589,
                    "freq": 10403,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/PADI.png",
                        "corpaction": {
                            "active": false,
                            "icon": "https://assets.stockbit.com/images/corp_action_event_icon.svg",
                            "text": "Perusahaan Memiliki Corporate Action"
                        },
                        "notation": []
                    },
                    "nval_trend": []
                },
                {
                    "stock_code": "ADMR",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": -4877099000,
                    "lot": -25175,
                    "avg_price": 1933.6957764534682,
                    "freq": 1355,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/ADMR.png?version=1753857326844772768",
                        "corpaction": {
                            "active": false,
                            "icon": "https://assets.stockbit.com/images/corp_action_event_icon.svg",
                            "text": "Perusahaan Memiliki Corporate Action"
                        },
                        "notation": []
                    },
                    "nval_trend": []
                },
                {
                    "stock_code": "KRAS",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": -4803164600,
                    "lot": -160539,
                    "avg_price": 299.5452995717434,
                    "freq": 2206,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/KRAS.png",
                        "corpaction": {
                            "active": false,
                            "icon": "https://assets.stockbit.com/images/corp_action_event_icon.svg",
                            "text": "Perusahaan Memiliki Corporate Action"
                        },
                        "notation": []
                    },
                    "nval_trend": []
                },
                {
                    "stock_code": "ZATA",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": -4510134700,
                    "lot": -452817,
                    "avg_price": 100.59687531854676,
                    "freq": 18048,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/ZATA.png",
                        "corpaction": {
                            "active": false,
                            "icon": "https://assets.stockbit.com/images/corp_action_event_icon.svg",
                            "text": "Perusahaan Memiliki Corporate Action"
                        },
                        "notation": [
                            {
                                "notation_code": "L",
                                "notation_desc": "Perusahaan Tercatat belum menyampaikan laporan keuangan",
                                "icon_url": {
                                    "light_mode": "https://assets.stockbit.com/logos/notations/light/L.png",
                                    "dark_mode": "https://assets.stockbit.com/logos/notations/dark/L.png"
                                }
                            }
                        ]
                    },
                    "nval_trend": []
                },
                {
                    "stock_code": "INDF",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": -4198052500,
                    "lot": -6016,
                    "avg_price": 6973.679361179361,
                    "freq": 1457,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/INDF.png",
                        "corpaction": {
                            "active": false,
                            "icon": "https://assets.stockbit.com/images/corp_action_event_icon.svg",
                            "text": "Perusahaan Memiliki Corporate Action"
                        },
                        "notation": []
                    },
                    "nval_trend": []
                },
                {
                    "stock_code": "MDIA",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": -4150641600,
                    "lot": -535756,
                    "avg_price": 84.17880775756468,
                    "freq": 10797,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/MDIA.png",
                        "corpaction": {
                            "active": false,
                            "icon": "https://assets.stockbit.com/images/corp_action_event_icon.svg",
                            "text": "Perusahaan Memiliki Corporate Action"
                        },
                        "notation": [
                            {
                                "notation_code": "L",
                                "notation_desc": "Perusahaan Tercatat belum menyampaikan laporan keuangan",
                                "icon_url": {
                                    "light_mode": "https://assets.stockbit.com/logos/notations/light/L.png",
                                    "dark_mode": "https://assets.stockbit.com/logos/notations/dark/L.png"
                                }
                            }
                        ]
                    },
                    "nval_trend": []
                },
                {
                    "stock_code": "LPPF",
                    "broker_code": "PD",
                    "type": "BROKER_TYPE_LOCAL",
                    "date": "2026-04-17",
                    "value": -3881177500,
                    "lot": -20010,
                    "avg_price": 1942.3451962608237,
                    "freq": 2937,
                    "company_detail": {
                        "icon_url": "https://assets.stockbit.com/logos/companies/LPPF.png",
                        "corpaction": {
                            "active": true,
                            "icon": "https://assets.stockbit.com/images/corp_action_event_icon.svg",
                            "text": "Perusahaan Memiliki Corporate Action"
                        },
                        "notation": []
                    },
                    "nval_trend": []
                }
            ]
        },
        "from": "2026-04-17",
        "to": "2026-04-17",
        "broker_code": "PD, XC, XL, YP",
        "broker_name": ""
    }
}

```

Withdrawn Detection:
```
fetch("https://exodus.stockbit.com/order-trade/order-queue?stock_code=WMUU&action_type=ACTION_TYPE_BUY&board_type=BOARD_TYPE_REGULAR&order_status=ORDER_STATUS_WITHDRAWN&limit=100&price=79", {
  "headers": {
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9",
    "authorization": "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6ImExNWQ5OGE2LTdkYzgtNDM3NS05NDk0LTEyOWJlM2RlODVkNCIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7InVzZSI6Im9qaW4iLCJlbWEiOiJvamluY2FzaEBnbWFpbC5jb20iLCJmdWwiOiJGYXV6YW4gUmFtYWRoYW4iLCJzZXMiOiJUMWJQNUdCTk1KRHgzV3JqIiwiZHZjIjoiNzlhYWNmOGFkZmY5MDM4YzQzMWExMDRkYTY0ZjdiNDciLCJ1aWQiOjYzODU2MSwiY291IjoiSUQifSwiZXhwIjoxNzc2NjE1MTk0LCJpYXQiOjE3NzY1Mjg3OTQsImlzcyI6IlNUT0NLQklUIiwianRpIjoiMTkzZGE2ZGQtZWQwMy00OTA2LWI4NGItODc1YzAwZTkyMjZjIiwibmJmIjoxNzc2NTI4Nzk0LCJ2ZXIiOiJ2MSJ9.PKhXDzsEJCwhR3KUGzoFGnA7i64Ce9_qi7lqboBU_DrF1dcSgfGBx1pCw0sK0UBL9jvoM03FsbV2RAQwdiWETuGZUTm6JXoIAScX9LFD4zyUiwAZDmAPGGrN3Op7w48uvYYJ4BNteARXEZ9eTsJl9PwLbC8EYuuLBeVia_TjYFB31p58ieYAzewbC_FNiJxt0VCSW_h5-3PWul7OqmR5VnfKsiKuC3LudKIjrwNJFA1Tas3g39ErIaSzz3LESbyzN7jJuKxl0NbhJLuFY_bzlrf7-DdXoeXQzrjSvZeyufLpOo_Jk7Lh6wbtg_duxe1-9UMAGCIauVcOVrGFooeA7Q",
    "sec-ch-ua": "\"Chromium\";v=\"116\", \"Not)A;Brand\";v=\"24\", \"Google Chrome\";v=\"116\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site"
  },
  "referrer": "https://stockbit.com/",
  "referrerPolicy": "strict-origin-when-cross-origin",
  "body": null,
  "method": "GET",
  "mode": "cors",
  "credentials": "include"
});

-- overall retail detector (1 freq small lot):
fetch("https://exodus.stockbit.com/order-trade/order-queue?stock_code=WMUU&action_type=ACTION_TYPE_BUY&board_type=BOARD_TYPE_REGULAR&order_status=ORDER_STATUS_ALL&limit=100&price=79", {
  "headers": {
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9",
    "authorization": "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6ImExNWQ5OGE2LTdkYzgtNDM3NS05NDk0LTEyOWJlM2RlODVkNCIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7InVzZSI6Im9qaW4iLCJlbWEiOiJvamluY2FzaEBnbWFpbC5jb20iLCJmdWwiOiJGYXV6YW4gUmFtYWRoYW4iLCJzZXMiOiJUMWJQNUdCTk1KRHgzV3JqIiwiZHZjIjoiNzlhYWNmOGFkZmY5MDM4YzQzMWExMDRkYTY0ZjdiNDciLCJ1aWQiOjYzODU2MSwiY291IjoiSUQifSwiZXhwIjoxNzc2NjE1MTk0LCJpYXQiOjE3NzY1Mjg3OTQsImlzcyI6IlNUT0NLQklUIiwianRpIjoiMTkzZGE2ZGQtZWQwMy00OTA2LWI4NGItODc1YzAwZTkyMjZjIiwibmJmIjoxNzc2NTI4Nzk0LCJ2ZXIiOiJ2MSJ9.PKhXDzsEJCwhR3KUGzoFGnA7i64Ce9_qi7lqboBU_DrF1dcSgfGBx1pCw0sK0UBL9jvoM03FsbV2RAQwdiWETuGZUTm6JXoIAScX9LFD4zyUiwAZDmAPGGrN3Op7w48uvYYJ4BNteARXEZ9eTsJl9PwLbC8EYuuLBeVia_TjYFB31p58ieYAzewbC_FNiJxt0VCSW_h5-3PWul7OqmR5VnfKsiKuC3LudKIjrwNJFA1Tas3g39ErIaSzz3LESbyzN7jJuKxl0NbhJLuFY_bzlrf7-DdXoeXQzrjSvZeyufLpOo_Jk7Lh6wbtg_duxe1-9UMAGCIauVcOVrGFooeA7Q",
    "sec-ch-ua": "\"Chromium\";v=\"116\", \"Not)A;Brand\";v=\"24\", \"Google Chrome\";v=\"116\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site"
  },
  "referrer": "https://stockbit.com/",
  "referrerPolicy": "strict-origin-when-cross-origin",
  "body": null,
  "method": "GET",
  "mode": "cors",
  "credentials": "include"
});

-- both response format:
{
    "message": "Successfully get list order queue",
    "data": {
        "orders": [
            {
                "id": "2812762000",
                "queue_number": "0",
                "stock_code": "WMUU",
                "time": "2026-04-17T08:58:00.000075Z",
                "action_type": "ACTION_TYPE_BUY",
                "price": 79,
                "status": "ORDER_STATUS_FULL_MATCH",
                "open": 0,
                "lot": 8000,
                "board_type": "BOARD_TYPE_REGULAR",
                "broker_code": "IU",
                "exchange_order_number": {
                    "full": "202604170000014107",
                    "formatted": "14107"
                },
                "queue_lot": 0,
                "broker_group": "BROKER_GROUP_LOCAL",
                "order_number": "202604170000014107"
            },
            {
                "id": "2812759365",
                "queue_number": "0",
                "stock_code": "WMUU",
                "time": "2026-04-17T08:58:00.000075Z",
                "action_type": "ACTION_TYPE_BUY",
                "price": 79,
                "status": "ORDER_STATUS_WITHDRAWN",
                "open": 0,
                "lot": 2000,
                "board_type": "BOARD_TYPE_REGULAR",
                "broker_code": "",
                "exchange_order_number": {
                    "full": "202604170000073832",
                    "formatted": "73832"
                },
                "queue_lot": 0,
                "broker_group": "BROKER_GROUP_UNSPECIFIED",
                "order_number": "202604170000073832"
            },
            {
                "id": "2812761255",
                "queue_number": "0",
                "stock_code": "WMUU",
                "time": "2026-04-17T08:58:00.000075Z",
                "action_type": "ACTION_TYPE_BUY",
                "price": 79,
                "status": "ORDER_STATUS_WITHDRAWN",
                "open": 0,
                "lot": 11,
                "board_type": "BOARD_TYPE_REGULAR",
                "broker_code": "",
                "exchange_order_number": {
                    "full": "202604170000152236",
                    "formatted": "152236"
                },
                "queue_lot": 0,
                "broker_group": "BROKER_GROUP_UNSPECIFIED",
                "order_number": "202604170000152236"
            },
            {
                "id": "2812761716",
                "queue_number": "0",
                "stock_code": "WMUU",
                "time": "2026-04-17T08:58:00.000075Z",
                "action_type": "ACTION_TYPE_BUY",
                "price": 79,
                "status": "ORDER_STATUS_WITHDRAWN",
                "open": 0,
                "lot": 1000,
                "board_type": "BOARD_TYPE_REGULAR",
                "broker_code": "",
                "exchange_order_number": {
                    "full": "202604170000190695",
                    "formatted": "190695"
                },
                "queue_lot": 0,
                "broker_group": "BROKER_GROUP_UNSPECIFIED",
                "order_number": "202604170000190695"
            },
            {
                "id": "2812761486",
                "queue_number": "0",
                "stock_code": "WMUU",
                "time": "2026-04-17T08:58:00.000075Z",
                "action_type": "ACTION_TYPE_BUY",
                "price": 79,
                "status": "ORDER_STATUS_WITHDRAWN",
                "open": 0,
                "lot": 50,
                "board_type": "BOARD_TYPE_REGULAR",
                "broker_code": "",
                "exchange_order_number": {
                    "full": "202604170000250466",
                    "formatted": "250466"
                },
                "queue_lot": 0,
                "broker_group": "BROKER_GROUP_UNSPECIFIED",
                "order_number": "202604170000250466"
            },
            {
                "id": "2812761692",
                "queue_number": "0",
                "stock_code": "WMUU",
                "time": "2026-04-17T08:58:00.000075Z",
                "action_type": "ACTION_TYPE_BUY",
                "price": 79,
                "status": "ORDER_STATUS_WITHDRAWN",
                "open": 0,
                "lot": 50,
                "board_type": "BOARD_TYPE_REGULAR",
                "broker_code": "",
                "exchange_order_number": {
                    "full": "202604170000271292",
                    "formatted": "271292"
                },
                "queue_lot": 0,
                "broker_group": "BROKER_GROUP_UNSPECIFIED",
                "order_number": "202604170000271292"
            },
            {
                "id": "2818575034",
                "queue_number": "0",
                "stock_code": "WMUU",
                "time": "2026-04-17T14:17:42.875834Z",
                "action_type": "ACTION_TYPE_BUY",
                "price": 79,
                "status": "ORDER_STATUS_FULL_MATCH",
                "open": 0,
                "lot": 1001,
                "board_type": "BOARD_TYPE_REGULAR",
                "broker_code": "EP",
                "exchange_order_number": {
                    "full": "202604170004164612",
                    "formatted": "4164612"
                },
                "queue_lot": 0,
                "broker_group": "BROKER_GROUP_LOCAL",
                "order_number": "202604170004164612"
            }
        ],
        "is_open_market": false,
        "pagination": {
            "has_next_page": true
        }
    }
}
