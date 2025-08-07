# RU_Bookmate_downloader
## Установка зависимостей:
`pip install -r requirements.txt`

## Авторизоваться в аккаунт Яндекс
![Авторизация](https://github.com/kettle017/RU_Bookmate_downloader/assets/37309120/bb3453eb-5d44-4410-b2e1-05193c88333e)

## Примеры запуска скрипта:
Для определения нужного флага смотрите на URL, в нем всегда есть подсказка: https://bookmate.ru/<флаг>/<id>\

### Основные команды:
1. Скачать аудиокнигу в максимальном качестве:\
`python RUBookmatedownloader.py audiobook <id> --max_bitrate`
2. Скачать аудиокнигу в обычном качестве:\
`python RUBookmatedownloader.py audiobook <id>`
3. Скачать аудиокнигу без объединения глав:\
`python RUBookmatedownloader.py audiobook <id> --no-merge`
4. Скачать аудиокнигу и сохранить отдельные главы после объединения:\
`python RUBookmatedownloader.py audiobook <id> --keep-chapters`
5. Скачать текстовую книгу:\
`python RUBookmatedownloader.py book <id>`
6. Скачать комикс:\
`python RUBookmatedownloader.py comicbook <id>`
7. Скачать текстовую книгу, разбитую на несколько частей:\
`python RUBookmatedownloader.py serial <id>`
8. Скачать серию текстовых книг, аудиокниг или комиксов:\
`python RUBookmatedownloader.py series <id>`

### Объединение глав аудиокниг:
По умолчанию главы аудиокниг объединяются в один файл автоматически. Если вы скачали главы отдельно или хотите перезаписать существующую объединённую аудиокнигу:

1. Объединить одну аудиокнигу:\
`python merge_audiobook.py "путь/к/папке/аудиокниги"`
2. Объединить все аудиокниги в папке mybooks/audiobook/:\
`python merge_audiobook.py --batch`
3. Принудительно перезаписать существующие объединённые файлы:\
`python merge_audiobook.py --batch --force`
4. Сохранить отдельные главы после объединения:\
`python merge_audiobook.py --batch --keep-chapters`

**Примечание:** По умолчанию отдельные файлы глав удаляются после успешного объединения для экономии места. Используйте `--keep-chapters` чтобы сохранить их.
