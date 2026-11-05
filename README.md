# MIT Degree Map: what's free on OpenCourseWare

Every MIT undergraduate degree program, every course on its official degree chart, and whether you can study that course for free on [MIT OpenCourseWare](https://ocw.mit.edu) (OCW).

**Live site:** https://dhyanpatel9.github.io/MIT-ocw-degree-map/

## What's in it

- **55 undergraduate programs** plus MIT's core requirements (calculus, physics, chemistry, biology)
- **1,108 courses**, each labeled:
  - **Required**, **Required – choose one** (pick one from a group), or **Elective option**
  - **On OCW**, **On OCW under another number** (e.g. the pre-2022 number), or **Not on OCW**
- A direct **link to the course materials** on OCW
- **More free materials**: MIT course websites, MITx courses on edX that are free to audit, and quick searches of [MIT Learn](https://learn.mit.edu) and YouTube

| | Courses |
|---|---|
| On OCW | 408 |
| On OCW under another number | 80 |
| Not on OCW | 620 (mostly elective options) |

*As of the November 5, 2026 refresh. The live site always shows the latest numbers.*

## Use the data

- [`data/courses.csv`](data/courses.csv): open in Excel or Google Sheets
- [`data/courses.json`](data/courses.json): for code

## How it works

[`scraper/refresh.py`](scraper/refresh.py):

1. Reads every undergraduate degree chart on [catalog.mit.edu](https://catalog.mit.edu/degree-charts/).
2. Works out which courses are required, choose-one or electives, from the chart's layout.
3. Loads OCW's full course list from its sitemap.
4. Matches each course to OCW by number. If there's no match, it tries the course's pre-2022 number (MIT renumbered most EECS courses in 2022), its joint number, then its exact title.

[`scraper/extras.json`](scraper/extras.json) holds hand-checked additions: joint course numbers, overrides, and links to free materials outside OCW.

A [GitHub Action](.github/workflows/refresh.yml) re-runs the scraper on the 1st of every month and commits any changes, so the data stays current.

### Run it yourself

```bash
pip install -r scraper/requirements.txt
python3 scraper/refresh.py      # updates data/
python3 -m http.server          # then open http://localhost:8000
```

## Known limitations

- The "Required?" labels are inferred from the layout of the catalog tables. A few programs with unusual layouts may be slightly off, so check the program's catalog link for the official requirements.
- Matches by an older number or by title are automated. Each one shows which OCW course it matched, so you can check it.
- OCW courses are free to study, but they don't give MIT credit or a degree.

Spotted a mistake? [Open an issue](https://github.com/Dhyanpatel9/MIT-ocw-degree-map/issues) or send a pull request (most fixes go in `scraper/extras.json`).

## License and credits

- Code: [MIT License](LICENSE)
- Compiled data (`data/`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- Course numbers, titles and requirements come from the [MIT Course Catalog](https://catalog.mit.edu). Course materials are hosted by [MIT OpenCourseWare](https://ocw.mit.edu) under CC BY-NC-SA 4.0. This repository links to them and does not copy them.

This is an independent project. It is not affiliated with or endorsed by MIT.
