return {
  {
    "mfussenegger/nvim-lint",
    opts = {
      linters = {
        ["markdownlint-cli2"] = {
          args = { "--config", "/home/do3cc/.markdownlint.jsonc", "--" },
        },
      },
    },
  },
}