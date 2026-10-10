---
name: shell-submit-skips-prevented
description: Перехватчик submit оболочки SPA пропускает формы с e.defaultPrevented — иначе форма с @submit.prevent всё равно уходит POST-ом на адрес страницы
stack: [vue, web-ui]
status: candidate
created: 2026-10-09
seen_in: [video-blade-2]
triggers:
  keywords: [перехват submit, '@submit.prevent', defaultPrevented, форма ушла на сервер, диалог закрылся сам, data-native]
  commands: []
  errors: []
  paths: ['frontend/src/App.vue', 'src/App.vue']
---
# Перехватчик submit оболочки SPA пропускает формы с e.defaultPrevented — иначе форма с @submit.prevent всё равно уходит POST-ом на адрес страницы

Контекст: оболочка кабинета слушает `submit` на документе и шлёт любую форму на сервер (редирект приходит JSON-ом).
Панель поиска и форма заказа внутри страницы, уже с `@submit.prevent`, всё равно улетали POST-ом на адрес страницы:
окно закрывалось само, заказ молчал — два круга ревью записали это как «кнопка не работает».

Урок:
- В глобальном обработчике первой строкой `if (e.defaultPrevented) return` (плюс явный признак вроде `data-native`
  для форм, которые должны уйти обычным путём браузера).
- Локальная форма страницы — всегда `@submit.prevent` и свой `fetch`; ответ показывай у самой формы.
- Признак: после «своей» кнопки страница перезагружается или окно закрывается само, в сети — POST на адрес страницы.
