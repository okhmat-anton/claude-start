---
name: capacitor-ios-screen-in-chrome
description: Экран Capacitor-приложения в iOS-виде снимается в Chrome без симулятора — CapacitorCustomPlatform и заглушка плагина до скриптов страницы; сервер — свой адрес
stack: [any, web-ui]
status: candidate
created: 2026-11-27
seen_in: [gym-bro-3]
triggers:
  keywords: [capacitor, CapacitorCustomPlatform, ios-вид, как в айфоне, без симулятора, снимок экрана подписки, экран оплаты, storekit, нативный плагин, isNativePlatform]
  commands: ['addScriptToEvaluateOnNewDocument']
  errors: ['plugin is not implemented on']
  paths: ['**/capacitor.config.*']
---
# Экран Capacitor-приложения в iOS-виде — в Chrome, без симулятора

Контекст: нужен снимок экрана, который в браузере выглядит иначе, чем в приложении (оплата через StoreKit вместо
сайта), — для проверяющего App Store или для ревью. Снимок с телефона ждёт сборку и руки владельца, симулятору для
цен StoreKit нужен свой файл настроек; экраны те же — их рисует и Chrome.

Урок:
- До скриптов страницы (CDP `Page.addScriptToEvaluateOnNewDocument`) задай `window.CapacitorCustomPlatform =
  {name: 'ios'}` — `getPlatform()` вернёт 'ios', `isNativePlatform()` — true; экраны покажут iOS-ветку.
- Нативный плагин замени заглушкой: `window.Capacitor = {PluginHeaders: [{name: 'Store', methods: [{name:
  'products', rtype: 'promise'}, …, {name: 'addListener', rtype: 'callback'}]}], nativePromise: (plugin, method,
  options) => …, nativeCallback: () => '<id>'}` — ядро Capacitor возьмёт этот объект и отдаст методы с заголовком
  в `nativePromise`. Ответы — те же, что дал бы плагин (цены магазина, валюта, срок).
- Плагины без заголовка и без web-реализации отвечают «not implemented on ios» — экран переживает это, если вызовы
  с `.catch`; плагины с web-реализацией работают.
- `isNativePlatform()` = true значит «сервер — полным адресом» (в приложении он боевой): запускай клиент стенда
  с переменной адреса сервера, равной самому стенду, и закрой боевой домен (`Network.setBlockedURLs`) — иначе
  снимок тихо возьмёт боевые данные.
- В сценарии снимка проверяй состояние до кадра (сколько карточек, нет строки ошибки): не тот человек или не дошедшие
  цены дают правдоподобный, но неверный снимок. Прерванный сценарий гасит Chrome в `finally`.
