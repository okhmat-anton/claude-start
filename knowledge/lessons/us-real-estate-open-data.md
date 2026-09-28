---
name: us-real-estate-open-data
description: Цены недвижимости США агенту: Redfin, Homes.com, LandSearch закрыты; Zillow — через Chrome без окна и открытые CSV индекса; Бюро переписи — xlsx по curl
stack: [any]
status: candidate
created: 2026-09-27
seen_in: [planning]
triggers:
  keywords: [цены домов, недвижимост, Zillow, Redfin, участк, real estate, фабричн, mobile home]
  commands: ['redfin\.com', 'zillow\.com']
  errors: []
  paths: []
---
# Цены недвижимости США: что открыто агенту

Контекст: ресёрч «окупится ли небольшой дом на продажу» — нужны цены домов, участков и фабричных домов
в конкретном округе. Сайты объявлений отдают запросу страницы 403 или 410.

Урок:
- Redfin, Homes.com, LandSearch, PropertyShark на WebFetch не тратить: закрыты. Цифры из их выдачи
  в поиске брать с пометкой «из поисковой выдачи».
- Zillow открывается настоящим Chrome без окна (тот же приём, что для Reddit): страницы поиска
  участков и фабричных домов отдают цену, площадь и адрес в тексте страницы.
- Индекс цен Zillow по трети рынка (дешёвая, средняя) по городам — открытые CSV:
  `files.zillowstatic.com/research/public_csvs/zhvi/City_zhvi_uc_sfrcondo_tier_0.0_0.33_sm_sa_month.csv`.
- Фабричные дома: таблицы Бюро переписи (цены по штатам и поставки по штатам) — xlsx по curl;
  xlsx читается без пакетов как zip с XML (sharedStrings + листы).
- Закрытые сделки так не достать: в отчёте писать «цены объявлений», а не «цены продаж».
