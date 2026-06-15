import { readFile, writeFile } from "node:fs/promises";

const USER = process.env.GH_USER;
const TOKEN = process.env.GH_TOKEN;
const FILE = "README.md";
const START = "<!-- ORGS:START -->";
const END = "<!-- ORGS:END -->";

const headers = {
  Accept: "application/vnd.github+json",
  "User-Agent": USER,
};
if (TOKEN) headers.Authorization = `Bearer ${TOKEN}`;

const res = await fetch(`https://api.github.com/users/${USER}/orgs`, { headers });
if (!res.ok) {
  console.error(`Erreur API GitHub : ${res.status}`);
  process.exit(1);
}

const orgs = await res.json();

let block = "";
if (orgs.length) {
  const logos = orgs
    .map((o) => {
      const url = new URL(o.avatar_url);
      url.searchParams.set("s", "64");
      return `<a href="https://github.com/${o.login}" title="${o.login}"><img src="${url}" width="42" height="42" alt="${o.login}"/></a>`;
    })
    .join("\n&nbsp;");
  block = `**Work at:**\n\n${logos}`;
}

const readme = await readFile(FILE, "utf8");
const pattern = new RegExp(`${START}[\\s\\S]*?${END}`);
if (!pattern.test(readme)) {
  console.error("Balises ORGS:START / ORGS:END introuvables dans le README.");
  process.exit(1);
}

await writeFile(FILE, readme.replace(pattern, `${START}\n${block}\n${END}`));
console.log(`OK — ${orgs.length} org(s) écrite(s).`);
