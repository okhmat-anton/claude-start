---
name: app-store-connect
description: Выкладка iOS-приложения в App Store Connect (11.2026) — сборка из терминала, снимки и Header, анкеты, Китай и DSA, подписки, черновик отправки
stack: [any]
triggers:
  keywords: [App Store Connect, TestFlight, выклад, на проверку, Submit for Review, черновик отправки, xcodebuild, exportArchive, возрастн, App Privacy, App Compliance, Retention Messaging, подписк, Prepare for Submission]
  commands: ['xcodebuild .*(archive|-exportArchive)', 'xcrun devicectl']
  errors: ['File dimensions are invalid', 'must be submitted with its subscription group']
  paths: ['**/ExportOptions*.plist', '**/*export*.plist', '**/*.xcodeproj/project.pbxproj']
---
# Стек: App Store Connect — как выглядит выкладка на деле (проверено 11.2026)

Справка Apple отстаёт от кабинета: ниже — как формы выглядели при первой выкладке, а не как описаны. Страница
продукта, поиск и правила 2.3/3.1 — заметка `app-store`. Запись приложения и подписки могли быть созданы раньше
под другими именами: каждый шаг инструкции начинай с «уже сделано?».

**Сборка и загрузка без окна Xcode**
- Archive: `xcodebuild -project App.xcodeproj -scheme App -configuration Release -destination 'generic/platform=iOS'
  -allowProvisioningUpdates -archivePath "$HOME/Library/Developer/Xcode/Archives/<дата>/<имя> <версия>.xcarchive"
  archive` — архив виден в Organizer.
- Загрузка: `xcodebuild -exportArchive -archivePath … -exportOptionsPlist … -exportPath … -allowProvisioningUpdates`;
  в plist: `method` app-store-connect, `destination` upload, `signingStyle` automatic, `teamID`,
  `manageAppVersionAndBuildNumber` **false** (иначе Xcode сам поднимает номер сборки), `uploadSymbols` true. В конце
  «Upload succeeded», обработка 5–30 минут. Номер сборки — урок `ios-build-number-never-reused`.
- Дев-сборка на свой iPhone: `xcodebuild … -configuration Debug -destination 'generic/platform=iOS' build`, затем
  `xcrun devicectl device install app --device <id> <…/Debug-iphoneos/App.app>` и `xcrun devicectl device process
  launch --terminate-existing --device <id> <bundle id>`. `devicectl list devices` видит телефон «available (paired)»,
  когда xctrace пишет Offline, — собирай на generic, не на устройство. Заблокированный телефон: запуск — «Locked»,
  установка проходит.

**Страница версии**
- Поле Version = CFBundleShortVersionString сборки, иначе её не выбрать; новая запись версии создаётся с 1.0.
  Рядом с версией кабинет сам пишет номер сборки в скобках — это его формат, у себя так не пиши.
- Обязательный слот снимков (осень 2026) — **iPhone with Dynamic Island (medium display)**: 1206×2622 или
  1179×2556. 1320×2868 там — «File dimensions are invalid»: это необязательный большой экран. Вкладки iPad,
  iPhone Duo, Watch видны всегда — сборке только под iPhone не нужны; iPhone Duo (1398×2034, 2007×2853)
  потребуют сборки на SDK iOS 27.1, с апреля 2027.
- Блок **Header** (iOS 27): 5244×2950 или 3840×1646, PNG без альфы, главное в центре — края срезают iPhone и
  iPad; снимки экрана в поле не подходят. Галочку «Use header asset in search results» не ставь: в поиске
  останутся снимки с приложением.
- Языки — «Add <язык>» в списке справа вверху; пункты стоят вплотную — сверяй, что добавился нужный (лишний —
  «Remove <язык>», Save). Язык версии сам появляется в App Information.
- Адрес политики конфиденциальности вводится в App Privacy → Privacy Policy → Edit — отдельно на каждом языке.
- Пока версия в черновике отправки, тексты и снимки не правятся: убрать из черновика, поправить, добавить снова.

**Анкеты, страны, соответствие**
- Возраст — 7 шагов, итог Apple считает сама. Новые пункты: Social Media (лента, своя соцсеть — Yes) и Social Media
  Disabled for Users Under 13 (проверки возраста нет — No) → 13+.
- Материковый Китай: App Compliance спрашивает Security Assessment и AI Generated or Synthetic Content. С ИИ в
  приложении «No» ответить нельзя, а «Yes» требует отчёт регулятора и номер регистрации модели в CAC — исключи
  China mainland из стран приложения **и каждой подписки**; блок ICP после этого пропадает.
- Digital Services Act (ЕС): Business → Complete Compliance Requirements. Трейдеру — адрес (можно абонентский
  ящик), телефон и почта: Apple показывает их на странице в ЕС и подтверждает кодами.
- Налоговая форма: Apple подводит по ответам — W-9 при адресе в США, W-8BEN — иначе.
- Только iPhone: в Pricing and Availability сними Mac с Apple Silicon и Vision Pro. Только HTTPS — вопрос о
  шифровании: No.

**Подписки**
- Цена — из списка с поиском, редкие — за «See Additional Prices»; нет и там — нет вообще (урок
  `store-price-from-apple-grid`).
- Purchase Options по умолчанию разрешают несколько мест и продажу в Apple Business/School Manager: «No, don't allow
  multiseat purchases» (те снимаются сами) → Confirm. Страны — Select All вверху окна; у годовой блок делится на
  «1 Year Upfront» и «Monthly with a 12-Month Commitment» — настраивай только первый.
- Порядок уровней: Edit → отметить подписку → Edit Level → перетаскивание за значок слева; брошенная на строку
  встаёт на тот же уровень, в промежуток между блоками — на свой.
- Server Notifications — только поле адреса (выбора Version 1/2 нет); Production и Sandbox задаются отдельно.
- Retention Messaging (сообщение при отмене): заголовок до 66 знаков, текст до 144, без цен и скидок; Apple просит
  сказать, что человек теряет.
- Review Information у товара: снимок обязателен — без него статус Missing Metadata, с ним Ready to Submit
  (урок `iap-review-screenshot-per-product`). Ключ Sign in with Apple (.p8) отдаётся один раз — храни вне репозитория;
  Services ID нужен только для входа на сайте, приложению — нет.

**Черновик отправки** (App Review → Drafts)
- Версия — Add for Review на её странице; подписки — на странице группы: Edit → отметить все → Add for Review →
  существующий черновик; **группа — отдельной кнопкой Add for Review вверху её страницы** (иначе «Your auto-renewable
  subscription must be submitted with its subscription group»); сообщение при отмене — своей кнопкой.
- Submit for Review, Release This Version и подпись договоров — только владелец. Демо-вход для проверяющего —
  урок `apple-review-demo-account`; агент в браузере — урок `browser-agent-react-forms`.
