---
name: video-ffmpeg-pitfalls
description: ffmpeg-грабли склейки — amix normalize=0, zoompan без -loop, одинаковые дорожки для concat, после concat settb=AVTB и fps перед xfade, эффект смотреть до конца
stack: [ffmpeg]
status: mature
created: 2026-07-26
seen_in: [work-video-production, kitchens, sofa-catalog]
triggers:
  keywords: [ffmpeg, склейк, concat, xfade, amix, zoompan, кроссфейд, timebase, frame rate, сегмент длиннее, звук едет]
  commands: ['ffmpeg\s.*(concat|xfade|amix|zoompan)']
  errors: ['timebase .* do not match', 'inputs needs to be a constant frame rate', 'Invalid data found when processing input']
  paths: []
---
# ffmpeg-грабли склейки

Контекст: сборка «часть склеек жёсткие (concat), часть кроссфейдом (xfade)» ломается двумя разными ошибками
подряд; сегменты из фото выходили кратно длиннее; подмешанный звук проседал.

Урок:
- `amix` по умолчанию делит громкость на число входов — всегда `normalize=0` + `alimiter`.
- `zoompan` на `-loop 1` выдаёт d кадров на КАЖДЫЙ входной кадр — подавай одно изображение без `-loop`,
  длину задавай `-frames:v`.
- Сегменты для `concat` обязаны иметь одинаковые дорожки: фото и заглушкам добавляй тишину (`anullsrc`).
- xfade после concat: (1) `timebase do not match` → `settb=AVTB` в конец каждого сегмента и после каждого
  concat/xfade; (2) `needs to be a constant frame rate` → `fps=N` после `concat` и после каждого `setpts`.
- Не проси у фото-модели «пустое место под текст» — зальёт зону однотонным полем; текст всегда оверлеем в монтаже.
- Эффект перехода (искры, вспышка) смотри до конца ДО нарезки: обрезка под тайминг сценария убивает эффект в разгаре — подгоняй соседние сцены.
