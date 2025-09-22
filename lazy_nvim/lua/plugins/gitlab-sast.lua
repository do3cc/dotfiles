return {
  "nvim-lua/plenary.nvim",
  event = "VeryLazy",
  config = function()
    local function read_json_file(path)
      local Path = require("plenary.path")
      local file = Path:new(path)
      if not file:exists() then
        vim.notify("❌ SAST report not found: " .. path, vim.log.levels.ERROR)
        return nil
      end

      local content = file:read()
      local ok, data = pcall(vim.fn.json_decode, content)
      if not ok then
        vim.notify("❌ Failed to parse JSON: " .. data, vim.log.levels.ERROR)
        return nil
      end

      if type(data) ~= "table" then
        vim.notify("❌ Unexpected JSON structure: root is not a table", vim.log.levels.ERROR)
        return nil
      end

      if not data.vulnerabilities or type(data.vulnerabilities) ~= "table" then
        vim.notify("❌ JSON does not contain a 'vulnerabilities' array", vim.log.levels.ERROR)
        return nil
      end

      vim.notify("✅ JSON file parsed successfully with " .. #data.vulnerabilities .. " entries", vim.log.levels.INFO)
      return data.vulnerabilities
    end

    local function load_sast_diagnostics(report_path)
      print("🔍 Loading SAST diagnostics from: " .. report_path)
      local data = read_json_file(report_path)
      if not data then
        return
      end

      local diagnostics_by_file = {}
      local severity_map = {
        Critical = vim.diagnostic.severity.ERROR,
        High = vim.diagnostic.severity.WARN,
        Medium = vim.diagnostic.severity.INFO,
        Low = vim.diagnostic.severity.HINT,
      }

      local total_issues = 0
      local skipped = 0

      for i, vuln in ipairs(data) do
        print("🔎 Processing entry " .. i .. ": " .. vim.inspect(vuln))

        if type(vuln) ~= "table" then
          vim.notify("⚠️ Skipping invalid entry at index " .. i, vim.log.levels.WARN)
          skipped = skipped + 1
          goto continue
        end

        local file = vuln.location and vuln.location.file
        local line = vuln.location and vuln.location.start_line
        local message = vuln.name
        local severity = vuln.severity

        if not (file and line and message and severity) then
          vim.notify("⚠️ Skipping incomplete entry at index " .. i, vim.log.levels.WARN)
          skipped = skipped + 1
          goto continue
        end

        if not severity_map[severity] then
          vim.notify("⚠️ Unknown severity: " .. tostring(severity), vim.log.levels.WARN)
        end

        local diag = {
          lnum = line - 1,
          col = 0,
          message = string.format("[%s] %s", severity, message),
          severity = severity_map[severity] or vim.diagnostic.severity.INFO,
          source = "GitLab SAST",
        }

        diagnostics_by_file[file] = diagnostics_by_file[file] or {}
        table.insert(diagnostics_by_file[file], diag)
        total_issues = total_issues + 1

        ::continue::
      end

      local ns = vim.api.nvim_create_namespace("sast")

      for file, diags in pairs(diagnostics_by_file) do
        local bufnr = vim.fn.bufnr(file, true)
        vim.diagnostic.set(ns, bufnr, diags, {})
        print("📌 Set diagnostics for " .. file .. " with " .. #diags .. " issues")
      end

      vim.notify(string.format("✅ SAST diagnostics loaded: %d issues, %d skipped", total_issues, skipped), vim.log.levels.INFO)
    end

    vim.api.nvim_create_user_command("LoadSAST", function(opts)
      print("🚀 LoadSAST command triggered with path: " .. opts.args)
      load_sast_diagnostics(opts.args)
    end, {
      nargs = 1,
      complete = "file",
      desc = "Load GitLab SAST diagnostics from JSON file",
    })

    print("✅ SAST plugin loaded")
  end,
}

