# Как писать техзадания для людей и для ИИ-агентов — опыт Reddit и навык spec-write

13.11.2026 · проект claude-start · сырьё (35 обсуждений Reddit с комментариями) — в рабочей папке сессии, в git не идёт.

## Вопрос

Владелец попросил создать протокол и навык написания и доработки техзадания (ТЗ) и перед этим изучить на Reddit, как
лучше писать ТЗ для людей и для агентов. Его алгоритм доработки, дословно по сути: после написания пройти по очереди
по каждому пункту; двоякий пункт — предложить, как дополнить, с вариантами ответа; конфликтующий — как исправить;
исправил уже пройденный пункт — пройти его заново; ждёшь неточностей — уточняющие вопросы с вариантами; пункт даёт
слабое место или уязвимость — решения с вариантами; ТЗ всегда рассчитано на запуск и выполнение в один заход, но по
этапам, с точками, где человек проверяет этап и поправляет; вопросы — всегда по одному, не пачкой.

## Коротко

- **Алгоритм владельца совпадает с лучшим опытом Reddit** в трёх местах: агент не переспрашивает, а угадывает,
  поэтому двоякое надо снимать до начала; у ТЗ, написанных моделью, типовой порок — противоречия между пунктами;
  человека останавливают там, где переделка дорога.
- **Чего в алгоритме не было, а Reddit даёт:** пункт должен проверяться («сделано / не сделано», числа вместо
  прилагательных); раздел «чего намеренно не делаем»; рецензент, который видит только ТЗ и код; программа, которая
  проверяет ссылки ТЗ на файлы; отчёт исполнителя «что вы должны увидеть»; лекарства от раздувания.
- **Главный спор** — нужно ли ТЗ заранее («обязательно» против «требования не пишутся, а открываются») и сколько
  вопросов задавать. Навык отвечает обоим: сценарий и показ работающего на каждом этапе открывают требования по
  ходу, а вопрос задаётся только там, где два независимых читателя поняли пункт по-разному.
- Что применено — таблица в конце; замер на ТЗ с заложенными пороками — раздел «Замер».

## Оговорки

- Поиск Reddit по словам закрыт («You've been blocked by network security»), старый интерфейс требует входа.
  Обсуждения найдены через ленты «лучшее» и блок «похожие обсуждения». Отсюда перекос к веткам про разработку «от
  ТЗ» (spec-driven development) и много веток с малым числом голосов.
- Почти пусто по темам: разбор угроз на стадии требований, «один заход против этапов», INVEST, definition of done.
  Не читались r/cursor, r/LLMDevs, r/vibecoding, r/webdev, r/programming, r/agile.
- Прямого обсуждения «вопросы по одному с вариантами» нет: найдены «2–3 круга по 4–6 вопросов», «нумерованный
  список» и «лимит в три вопроса». Правило «по одному» — правило владельца, а не вывод из Reddit.
- Цитаты сверены программой с сохранёнными страницами (94 из 94) и выборочно вручную (12 из 12). Замеры из веток —
  слова авторов, не проверены. В скобках после ника — голоса комментария; «пост [N]» — голоса поста.

## 1. ТЗ для людей

1. **Сначала потребность, потом требования.** «I separate needs and requirements. Business can express a need, but
   needs are not requirements.» — u/Jojje22 [55], https://www.reddit.com/r/businessanalysis/comments/1kmc8xe/
2. **Обязательные разделы:** цель, рамки «делаем / намеренно не делаем», словарь, требования, ограничения, история
   правок. «Scope - what is being done, and perhaps even more importantly, what is intentionally not being done» —
   u/mister-noggin [7], https://www.reddit.com/r/ProductManagement/comments/16isvyp/
3. **Пункт проверяем:** «прошёл / не прошёл», числа с единицами, без оценочных слов. «If you can’t envision any way
   to verify a requirement, then you probably have a bad requirement.» — u/Royal_Network6112 [11]; «Adjectives are
   bad. Absolute adjectives are a mortal sin. It needs to have numbers and units.» — u/NotYourGolChappati [4],
   https://www.reddit.com/r/systems_engineering/comments/1xe3sr7/
4. **Условие — в начале пункта** (шаблон EARS: IF, WHEN, WHILE); пункт с исключениями режется на несколько. —
   u/Aerothermal [28], там же.
5. **Требование и обоснование — раздельно.** Проверочный вопрос к пункту: «would someone be unhappy if this weren't
   true?» — u/half_integer [3], https://www.reddit.com/r/systems_engineering/comments/1s1tqwv/
6. **Критерии приёмки — из вопроса о готовом результате.** «Ask "what needs to be true when this is done" and build
   from there.» — u/lexpectopatronum [15], 1kmc8xe.
7. **Глубина — по исполнителю.** «Working with a great team of in-house engineers, 'good requirements' might be a
   1-pager and a few diagrams.» — u/Dylando_Calrissian [21], https://www.reddit.com/r/ProductManagement/comments/17ha1lo/
8. **Пример исполняют буквально.** «added a step to supersede the answer with a hard coded “4” because that’s what
   my test case said» — пост [125], https://www.reddit.com/r/ProductManagement/comments/1icxcyp/
9. **Пересказать своими словами и вернуть на подтверждение.** «Key thing is to not use their words or phrases in
   your document.» — u/imagei [3], https://www.reddit.com/r/SoftwareEngineering/comments/1ihv24b/ ; неверный
   черновик вытягивает требования: «The best way to get the right specifications is to provide the wrong
   dashboard.» — u/MaartenHH [7], 1kmc8xe.

## 2. ТЗ для агентов

1. **Агент не переспрашивает, а угадывает.** «with an AI coding tool I write down more of the edge cases than I
   would for a person, since it won't stop and ask when something's unclear. It just guesses and moves on.» —
   u/Helpful-Pool-8817 [4], https://www.reddit.com/r/ProductManagement/comments/1wmtmq1/
2. **Точность там, где опасно, а не объём.** «Precision where it counts, not volume everywhere.» —
   u/Worldofbarca [3], https://www.reddit.com/r/businessanalysis/comments/1u514kl/
3. **Одно ТЗ — одно изменение: цель, шаги, признак готовности.** — пост [45],
   https://www.reddit.com/r/ClaudeCode/comments/1xh40ny/
4. **Порядок действий в ТЗ не писать.** «The agent turned that into acceptance criteria and failed a run that was
   actually correct.» — тот же пост.
5. **Неприкосновенные правила — отдельно; прошлые решения записывать.** «The spec didn't mention the prior
   decision.» — пост [10], https://www.reddit.com/r/AI_Agents/comments/1ta2dfz/
6. **Запрет словами слаб: писать, что можно.** «if you don’t want it to do don’t mention it, mention the correct
   thing to do instead» — u/kincaidDev [4]; «Prompt rules are fine for preferences, never for secrets.» —
   u/BarathKanna [2], https://www.reddit.com/r/aiagents/comments/1xqjioz/
7. **Заранее записать, какие файлы меняются и какие нельзя трогать.** — пост [6],
   https://www.reddit.com/r/ClaudeAI/comments/1wkktmh/
8. **Коротко и проверено.** «Specs don't need to be as precise as the code they produce. They need to be short,
   verified» — пост [45], 1xh40ny.
9. **Один термин — одно значение.** «We have multiple terms that refer to the same thing for example, and it just
   produces stuff we never asked for» — u/TelephoneSignal3238 [4], 1xh40ny.
10. **Полный цикл — только для крупного.** «only do full SDD for new modules or features touching 200+ LOC» —
    пост [23], https://www.reddit.com/r/SpecDrivenDevelopment/comments/1tfkemy/

## 3. Доработка ТЗ до начала работы

1. **Каждый вопрос обязан менять результат; сначала читать файлы.** «Every question must be able to change the
   build.» — пост с текстом навыка [169], https://www.reddit.com/r/ClaudeAI/comments/1vk0tps/ ; «Inspect the
   material first. Ask only about unknowns that would change the result; otherwise state your assumptions and
   proceed.» — u/benjzammit01 [1], https://www.reddit.com/r/ClaudeAI/comments/1xrtmvs/
2. **Ответ вписывается в ТЗ.** «when it does ask, the answer goes back into the spec file» —
   u/Plastic-Risk-6309 [1], https://www.reddit.com/r/ClaudeAI/comments/1vr72hz/
3. **Рецензент «с чистого листа» видит только ТЗ и код.** «They read only your .md spec and repo cold as adversarial
   reviewers to expose edge cases and ambiguities before any code is written.» — пост [804],
   https://www.reddit.com/r/ClaudeAI/comments/1xkn61s/
4. **Рецензия кончается вердиктом; ссылки ТЗ на файлы проверяет программа.** «A script first checks that every file
   and line the spec cites actually exists. Then the reviewer answers BUILD, BUILD WITH CUTS or REFUSE.» —
   пост [45], 1xh40ny.
5. **Помечать непроверенное.** «marking the parts of the plan the planning session couldn't check against the real
   code. Those get verified first» — u/Technical-Pianist365 [1], https://www.reddit.com/r/ClaudeAI/comments/1w58l5u/
6. **ТЗ от модели, не прочитанное человеком, не работает.** «I've seen devs write 1-2 sentence prompts, generate the
   specs and then open a PR without reading the output.» — u/illuminatedtiger [259],
   https://www.reddit.com/r/ExperiencedDevs/comments/1xe74cu/
7. **Противоречия между пунктами — типовой порок ТЗ от модели.** «at least 30% of the content repeated with
   conflicting requirements between paragraphs» — u/TheAnxiousDeveloper [57],
   https://www.reddit.com/r/ExperiencedDevs/comments/1x5u8bn/

## 4. Исполнение по ТЗ

1. **Этап — кусок на один просмотр.** «I try to make the tasks PR-size in general.» — u/eastwindtoday [2],
   https://www.reddit.com/r/ClaudeCode/comments/1op8b6i/
2. **Контрольная точка — коммит, привязанный к пункту ТЗ.** «every meaningful chunk of work gets its own commit, you
   review 40-50 lines at a time instead of 400» — u/hallucinagentic [1], 1ta2dfz.
3. **Галочки по этапам и журнал отступлений; потом ТЗ правится по факту.** «to keep checkboxes up to date as it
   progresses, and to list any deviation in a notes section» — u/Due_Hovercraft_2184 [11],
   https://www.reddit.com/r/ClaudeCode/comments/1rus6zl/
4. **Отчёт по этапу — что человек должен увидеть.** «Tells me what I should be seeing in my personal testing.» —
   u/MeretrixDominum [3], 1w58l5u.
5. **Ворота для человека — там, где откат дорог.** «the gates that held up for me are the ones where undoing the step
   is expensive. The per-stage approvals died on their own» — u/Technical-Pianist365 [1], 1w58l5u.
6. **«Готово» проверяет другая модель с чистым контекстом по заранее записанной проверке.** — u/devdnn [2],
   https://www.reddit.com/r/SpecDrivenDevelopment/comments/1sexm55/

## 5. Где ТЗ для агентов проваливаются

1. **Раздувание.** «One wrote 13 tasks for that sentence, another 24, another 29» — пост [6], 1wkktmh.
2. **Планы перестают читать.** «I hit approve and hope for the best. That's not planning, that's a ritual.» —
   пост [3], https://www.reddit.com/r/ClaudeCode/comments/1ws7gvb/
3. **Устаревание.** «the model will faithfully implement a requirement you already changed your mind on three
   sessions ago» — u/ultrathink-art [7], 1rus6zl.
4. **«Готово» без проверки.** «It SAID it did what the spec said, but really it was just an approximation» —
   u/brennhill [2], 1sexm55.
5. **Модель пишет ТЗ и сама исполняет.** «SDD has not removed the error. It has formalized it.» — пост [60],
   https://www.reddit.com/r/SpecDrivenDevelopment/comments/1vubvmz/

## Спорные места

- **Нужно ли ТЗ заранее** (все — 1xe74cu). За: «I’m convinced that writing specs is basically mandatory for working
  with agents.» — u/editor_of_the_beast [141]. Против: «Specs are not written, they are discovered.» — u/mmcnl [154].
  Условно: «Spec driven development works if you know how to write specs.» — u/c-digs [445].
- **Окупается ли.** Против: «The spec-driven runs typically consume two to three times as many tokens and take about
  twice as long.» — пост [60], 1vubvmz. За: набор с ТЗ вышел в 9 раз дороже, но поймал два крайних случая —
  пост [1], https://www.reddit.com/r/ClaudeAI/comments/1xof63m/
- **Длина.** «try 400 pages» — u/PopeSalmon [8] против «1 page of PDF» — u/evanthebouncy [4],
  https://www.reddit.com/r/ChatGPTCoding/comments/1o6j1yr/
- **Допрос.** За: «`grilling` consistently discovers ambiguity in requirements and leads to higher quality specs and
  tickets.» — u/toby_hede [2], 1vr72hz. Против: девять лишних вопросов из десяти — пост [2], там же. Ответ:
  «you are the conductor though....if it gets exhausting just say you are done and move forward» —
  u/Vancecookcobain [12], https://www.reddit.com/r/codex/comments/1ugrxzd/

## Что применено в навыке spec-write

| Вывод | Где в навыке |
|---|---|
| потребность раньше требований; приёмка из «что должно быть верно, когда готово» (1.1, 1.6) | разделы ТЗ «Зачем» и «Что вы увидите, когда готово» — сценарий пишется первым и служит приёмкой |
| «намеренно не делаем» (1.2) | обязательный раздел «Чего не делаем» с «Потом» |
| пункт проверяем, числа вместо прилагательных, условие в начале (1.3, 1.4) | форма пункта, шесть вопросов к пункту; программа отмечает расплывчатые слова |
| пересказ своими словами (1.9) | сценарий пишется не словами владельца; читатели пересказывают пункты своими словами |
| агент угадывает (2.1); каждый вопрос меняет результат (3.1) | проход по пунктам; вопрос — только где читатели разошлись или развилка по факту |
| порядок действий не писать; один термин — одно значение (2.4, 2.9) | правила пункта |
| файлы, которые меняются и которые нельзя трогать; прошлые решения (2.5, 2.7) | «Памятка исполнителю», таблица «Решения владельца» с отвергнутыми вариантами |
| полный цикл — только для крупного (2.10) | малое и полное ТЗ; предложение кнопкой, а не обязанность |
| ответ вписывается в ТЗ (3.2) | ответ сразу в пункт и в «Решения владельца» |
| рецензент с чистого листа, вердикт (3.3, 3.4) | два слепых читателя и рецензент простоты; вердикт «строить / с урезанием / не строить» |
| программа проверяет ссылки на файлы (3.4) | `tz.js check` |
| непрочитанное ТЗ не работает (3.6) | «Коротко» и сценарий; запуск только после чтения владельцем |
| противоречия между пунктами (3.7) | проверка «конфликт», подсказка «возможно связаны» |
| этап на один просмотр, коммит на этап, галочки и отступления (4.1–4.3) | «Этапы и точки проверки», «Ход исполнения» |
| отчёт «что вы должны увидеть» (4.4) | точка проверки — показ на стенде и названные шаги сценария |
| ворота там, где откат дорог (4.5) | стоп обязателен после первого видимого результата, перед необратимым и в конце; остальное — «без остановки — причина» |
| раздувание, устаревание (5.1, 5.3) | пункт без шага сценария не пишется; правка владельца сначала вносится в ТЗ; источник у каждого пункта |
| модель пишет и сама исполняет (5.5) | читатели — на модели исполнителя; исполнять можно в новой сессии и моделью попроще |

Своё, чего на Reddit не нашлось: расхождение двух читателей как признак двоякости (их прочтения — варианты ответа);
очередь прохода с отпечатком текста пункта (изменился после отметки — вернулся в очередь); источник у каждого пункта
и счёт «сколько придумал агент»; рецензент простоты, которому разрешено только убирать; запись вида пропуска на
точках проверки.

## Решения владельца — 13.11.2026

| Вопрос | Ответ |
|---|---|
| Когда навык включается | по слову владельца; в начале каждой средней и сложной задачи система предлагает кнопкой доработать постановку техзаданием |
| Что делает исполнитель на точке проверки | останавливается и ждёт; показывает работающее — поднимает локальный стенд или выкладывает на тестовый сервер онлайн |
| Где лежат документы | навык создаёт в проекте папку `technical-docs` и кладёт туда всё: ТЗ, протоколы, материалы |
| Удобство | обязательный раздел о том, как этим пользуются; функции продумываются заранее и не перегружаются — логика Джобса, правила Apple для приложений; отдельный агент смотрит ТЗ на перегруз и запутанность |
| Вопросы | всегда по одному, с вариантами ответа |

## Замер

Учебный проект «Заметки» и ТЗ с заложенными пороками лежат в `evals/spec-write/` (ключ — `KEY.md`). В ТЗ заложено
15 пороков — по три двояких пункта, конфликта, дыры, слабых места и перегруза, — три поломки строения и три «ложных
следа» (пункты, которые выглядят подозрительно, но чисты). Исполнители не видели ни ключа, ни чата.

| Кто | Модель | Пороков из 15 | Время | Что пропустил |
|---|---|---|---|---|
| Читатель 1 | попроще (sonnet) | 13 | 30 с | пустую корзину; ссылку на удалённую заметку |
| Читатель 2 | сильная (opus) | 14 | 2,5 мин | пустую корзину |
| Рецензент простоты | сильная (opus) | 15, один — слабо | 4 мин | — |
| Все трое | — | **15** | около 4 мин, параллельно | — |
| Свежий сильный агент: полный проход по навыку, один | самая сильная | **15** | 35 мин | — |
| Программа: поломки строения | — | 3 из 3 | мгновенно | — |

Что показал замер:

- **По находкам читатели и проход равны, по времени — нет.** Свежий сильный агент, который один идёт по навыку,
  нашёл те же 15 из 15, но за 35 минут; трое читателей — за четыре минуты и на моделях попроще, расход токенов
  примерно одинаковый (0,4 млн). Поэтому в навыке читатели запускаются первыми, а проход автора начинается
  с их находок.
- **Дешёвый читатель окупается**: модель попроще за полминуты находит 13 пороков из 15. ТЗ стоит читать той
  моделью, которая будет исполнять.
- **Рецензент простоты ловит то, что пропускают исполнители**: пустое состояние, вход на экран, отклик на действие —
  «без чего человек застрянет». Правило «только убирать» он соблюдает: добавил лишь это.
- **Совпавшая догадка — ещё не ответ.** Оба читателя независимо «додумали» срок жизни общедоступной ссылки —
  7 дней. Отсюда правило навыка: совпавшая догадка о деньгах, доступе, данных или необратимом — всё равно вопрос.
- **Сверх ключа** найдено около десяти настоящих пороков: данные в памяти против обещанных 30 дней; отключённая
  ссылка оживает при повторном «Поделиться»; стенд на локальном адресе не открыть с телефона; «окно без входа» на
  стенде не отличается от обычного; нет способа проверить 30 дней без сдвига времени.
- **Ложные следы** лишних вопросов не дали: по одному из них читатели задали уместный вопрос, которого в ключе нет.
- Расход: три свежих агента на одно ТЗ — около 0,4–0,5 млн токенов и пять минут.

**Второй замер — ТЗ, которое автор уже прошёл сам.** Свежий агент по короткой просьбе написал малое ТЗ (13 пунктов),
задал владельцу два вопроса по одному, дважды прошёл пункты и довёл до «готово к запуску»; после этого его прочитали
те же два читателя. Оба поставили «строить» и нашли только мелочи: одну фактическую ошибку (пример «в приватном режиме
не запоминается» неверен — запоминается), неназванный инструмент для кадров и способы проверить то, чего глазами не
видно. Вывод: после честного прохода автора читатели — страховка, а не источник крупных находок; малому ТЗ они не
нужны, полному — нужны.

Рецензент простоты на том же, уже пройденном ТЗ поставил 8 из 10 и нашёл то, чего не увидели ни автор, ни оба
читателя: на телефоне клавиатура закрывает найденное, а на пустой странице поле поиска стоит там, куда человека
зовут записать первую заметку. Отсюда правило навыка: рецензент простоты нужен и малому ТЗ, если человек что-то
видит на экране.

**Исполнение по ТЗ.** Свежий агент на модели попроще получил одну строку запуска, без навыка и без чата: за минуту
выполнил единственный этап, поднял локальный стенд, сам прогнал сценарий и остановился с отчётом по форме — где
смотреть, какие шаги пройти, что проверил сам и чего глазами не смотрел, где отступил от ТЗ, — записал ход
исполнения в ТЗ и закоммитил. Стенд и страница проверены отдельно кадрами на компьютере и телефоне. ТЗ
самодостаточно; чего не хватило исполнителю — названного инструмента для кадров, он добавлен в памятку шаблона.

На настоящем ТЗ (неисполненное ТЗ на 250 строк в проекте planning) два читателя разошлись в четырёх местах — что
входит в лимит, кто считает оценку, что с ходами под запрещённым, когда меняется статус, — нашли семь конфликтов
пунктов между собой и с кодом и утечку личных данных через ссылку без входа. Рецензент простоты поставил 5 из 10
и дал восемь предложений урезать: шесть настроек свести к двум, этап-дубль слить, одно слово в двух смыслах развести.

Оба автора пробных прогонов дали замечания к самому навыку (10 и 23) — они внесены: граница «допущение или вопрос»
(допущение — только то, что видно на первом показе, меняется за минуты и не про деньги, доступ, данные
и необратимое), что делать со следствиями ответа владельца, источник пункта по самому слабому звену, проход по всем
разделам, а не только по пунктам; из программы убрана подсказка «возможно связаны» — она не нашла ни одного из трёх
настоящих конфликтов.

Ревью кода программы свежим агентом нашло 12 ошибок, все исправлены и закреплены проверками (36 случаев в
`tz.test.js`). Главная: итог «исправлен» снимал пункт с очереди, хотя правило владельца — «исправленный пункт
проходится заново»; теперь «исправлен» оставляет пункт в очереди до итога «чисто».

## Прочитанные обсуждения — 35

Ссылка — название — голосов / комментариев всего / прочитано.

1. https://www.reddit.com/r/ClaudeAI/comments/1xkn61s/ — «For over a year…» — 804 / 112 / 99
2. https://www.reddit.com/r/ExperiencedDevs/comments/1x5u8bn/ — «Increasingly unreadable technical specs…» — 666 / 246 / 202
3. https://www.reddit.com/r/ExperiencedDevs/comments/1xe74cu/ — «Was Spec Driven Development a failure?» — 480 / 736 / 506
4. https://www.reddit.com/r/ClaudeAI/comments/1vk0tps/ — «Really love the grill-me…» — 169 / 44 / 35
5. https://www.reddit.com/r/ProductManagement/comments/1sno7vn/ — «“Requirements weren’t clear” is…» — 140 / 39 / 32
6. https://www.reddit.com/r/ProductManagement/comments/1icxcyp/ — «“Unclear Requirements”: How granular…» — 125 / 142 / 129
7. https://www.reddit.com/r/ClaudeCode/comments/1op8b6i/ — «Why we shifted to…» — 118 / 39 / 30
8. https://www.reddit.com/r/ClaudeAI/comments/1xrtmvs/ — «Asking Claude 'what do…» — 106 / 16 / 15
9. https://www.reddit.com/r/ChatGPTCoding/comments/1o6j1yr/ — «Spec-driven development for AI…» — 70 / 87 / 45
10. https://www.reddit.com/r/SpecDrivenDevelopment/comments/1vubvmz/ — «We tried spec-driven development…» — 60 / 34 / 29
11. https://www.reddit.com/r/businessanalysis/comments/ane2en/ — «First time doing a…» — 53 / 18 / 17
12. https://www.reddit.com/r/businessanalysis/comments/1g3r8ot/ — «How to Write a…» — 46 / 27 / 21
13. https://www.reddit.com/r/ClaudeCode/comments/1xh40ny/ — «1000+ specs, ~500k lines…» — 45 / 36 / 34
14. https://www.reddit.com/r/ProductManagement/comments/12w6fyg/ — «What is your process…» — 34 / 43 / 42
15. https://www.reddit.com/r/businessanalysis/comments/1kmc8xe/ — «How do you handle…» — 28 / 20 / 17
16. https://www.reddit.com/r/SoftwareEngineering/comments/1ihv24b/ — «How Do Experienced Developers…» — 27 / 30 / 21
17. https://www.reddit.com/r/ProductManagement/comments/17ha1lo/ — «What are “good requirements”?» — 24 / 14 / 14
18. https://www.reddit.com/r/SpecDrivenDevelopment/comments/1tfkemy/ — «Tried GitHub's spec-kit with…» — 23 / 10 / 7
19. https://www.reddit.com/r/systems_engineering/comments/1xe3sr7/ — «How to write Good…» — 20 / 15 / 12
20. https://www.reddit.com/r/BMAD_Method/comments/1r6aruo/ — «BMAD method sucks» — 18 / 33 / 33
21. https://www.reddit.com/r/systems_engineering/comments/1s1tqwv/ — «Examples of really good…» — 18 / 47 / 34
22. https://www.reddit.com/r/SpecDrivenDevelopment/comments/1sexm55/ — «I tested whether specs…» — 16 / 39 / 27
23. https://www.reddit.com/r/SpecDrivenDevelopment/comments/1uklhsi/ — «grill-with-docs versus spec driven» — 16 / 11 / 10
24. https://www.reddit.com/r/ClaudeCode/comments/1rus6zl/ — «Spec-Driven Development (SDD) frameworks…» — 14 / 36 / 27
25. https://www.reddit.com/r/businessanalysis/comments/1u514kl/ — «Requirements engineering and AI…» — 12 / 9 / 5
26. https://www.reddit.com/r/AI_Agents/comments/1ta2dfz/ — «Spec-driven agentic coding is…» — 10 / 13 / 12
27. https://www.reddit.com/r/ProductManagement/comments/16isvyp/ — «How to write a…» — 9 / 16 / 12
28. https://www.reddit.com/r/aiagents/comments/1xqjioz/ — «I tested 14 coding…» — 8 / 17 / 16
29. https://www.reddit.com/r/ProductManagement/comments/1wmtmq1/ — «How much of a…» — 7 / 30 / 25
30. https://www.reddit.com/r/ClaudeAI/comments/1wkktmh/ — «I measured what four…» — 6 / 21 / 18
31. https://www.reddit.com/r/ClaudeCode/comments/1ws7gvb/ — «Is plan mode still…» — 3 / 47 / 42
32. https://www.reddit.com/r/ClaudeAI/comments/1vr72hz/ — «Grill / plan skills…» — 2 / 17 / 6
33. https://www.reddit.com/r/codex/comments/1ugrxzd/ — «Does anyone else feel…» — 1 / 14 / 13
34. https://www.reddit.com/r/ClaudeAI/comments/1w58l5u/ — «Has anyone tried Spec-Driven…» — 1 / 29 / 22
35. https://www.reddit.com/r/ClaudeAI/comments/1xof63m/ — «Tried GitHub’s Spec Kit…» — 1 / 4 / 2
