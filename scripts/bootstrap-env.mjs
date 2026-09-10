import { copyFile, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";

const environmentFiles = [
  {
    example: "apps/web/.env.example",
    local: "apps/web/.env.local",
  },
  {
    example: "apps/backend/.env.example",
    local: "apps/backend/.env",
  },
];

for (const file of environmentFiles) {
  const examplePath = resolve(file.example);
  const localPath = resolve(file.local);

  if (existsSync(localPath)) {
    console.log(`Keeping existing ${file.local}`);
    continue;
  }

  await mkdir(dirname(localPath), { recursive: true });
  await copyFile(examplePath, localPath);
  console.log(`Created ${file.local} from ${file.example}`);
}
