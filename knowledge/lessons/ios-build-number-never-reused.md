---
name: ios-build-number-never-reused
description: Номер сборки в App Store Connect занят навсегда — журнал загрузок в репозитории, Archive не собирается с номером не новее журнала, Xcode номер сам не меняет
stack: [any]
status: candidate
created: 2026-11-27
seen_in: [gym-bro-3]
triggers:
  keywords: [номер сборки, build number, CFBundleVersion, CURRENT_PROJECT_VERSION, MARKETING_VERSION, manageAppVersionAndBuildNumber, загрузить в TestFlight, загрузка в App Store, xcarchive]
  commands: ['xcodebuild .*(archive|-exportArchive)']
  errors: ['bundle version must be higher', 'Redundant Binary Upload']
  paths: ['**/*.xcodeproj/project.pbxproj', '**/*export*.plist']
---
# Номер сборки в App Store Connect не переиспользуется — журнал загрузок и стоп в Archive

Контекст: за сутки в App Store Connect ушли четыре загрузки; первую Xcode перенумеровал сам, и номера в коде,
у сервера и в кабинете разошлись — следующая версия получила номер, обходящий занятые.

Урок:
- Номер сборки (CFBundleVersion), раз загруженный, занят навсегда — даже если сборку удалили или она не прошла.
  Веди журнал загрузок в репозитории (версия, дата, куда) и дописывай строку сразу после «Upload succeeded».
- Фаза сборки в Xcode (Run Script) останавливает Archive в Release, если номер не новее журнала или версия не
  в договорённом виде — ошибка ловится до загрузки, а не письмом из App Store Connect.
- В параметрах выгрузки `manageAppVersionAndBuildNumber` = false: по умолчанию Xcode сам поднимает номер и не говорит
  об этом — код и кабинет расходятся.
- Версию и номер во все места (приложение, расширения, код экранов, сервер) ставит один скрипт, тест сверяет. Правило
  владельца: версия только X.Y.N, последнее число — номер сборки этой версии; «(N)» нигде не пишется.
- В кабинете поле Version страницы версии = CFBundleShortVersionString сборки, иначе её не выбрать; новая запись
  версии создаётся с 1.0 — поменяй до выбора сборки.
- Занятые номера ломают схему «номер = последнее число версии» — следующая версия перепрыгивает их (после 4 —
  1.0.5), а не повторяет.
