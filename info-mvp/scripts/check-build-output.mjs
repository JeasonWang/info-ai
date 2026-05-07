import { stdin, stdout, stderr, exit } from "node:process";

const chunks = [];

stdin.setEncoding("utf8");
stdin.on("data", (chunk) => {
  chunks.push(chunk);
  stdout.write(chunk);
});

stdin.on("end", () => {
  const output = chunks.join("");
  const failedPatterns = [
    /Build failed/i,
    /\bERROR\b/i,
    /条件编译失败/,
    /缺少配对的\s+#endif/,
    /Failed to compile/i,
  ];

  const matched = failedPatterns.find((pattern) => pattern.test(output));
  if (matched) {
    stderr.write(`\nBuild verification failed: matched ${matched}\n`);
    exit(1);
  }
});
