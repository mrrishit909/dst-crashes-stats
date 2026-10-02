# The project's check: every model in results/models.csv and results/robustness.csv, refitted in R from results/daily.csv.
#   Rscript check.R
# R's glm with a quasi-Poisson family must give the same week-after coefficient and standard error as statsmodels
# (to 1e-6), and the placebo spread must leave the spring change outside it.
suppressMessages(library(tidyverse))
d <- read_csv("results/daily.csv", show_col_types = FALSE)
win <- function(g, col, days = 28) g |> filter(between(.data[[col]], -days, days + 6)) |>
  mutate(t = .data[[col]], week_after = as.integer(between(.data[[col]], 0, 6)))
est <- function(w, y = "crashes", extra = NULL) {
  f <- reformulate(c("week_after", "factor(year)", "factor(dow)", "t", extra), y)
  m <- glm(f, family = quasipoisson, data = w)
  s <- summary(m)$coefficients["week_after", ]
  c(coef = unname(s[1]), se = unname(s[2]))
}
py <- read_csv("results/models.csv", show_col_types = FALSE)
n <- 0
for (i in seq_len(nrow(py))) {
  g <- filter(d, group == py$group[i])
  col <- if (py$change[i] == "spring forward") "days_from_spring" else "days_from_fall"
  r <- est(win(g, col), py$outcome[i])
  stopifnot(abs(r["coef"] - py$coef[i]) < 1e-6, abs(r["se"] - py$se[i]) < 1e-6)
  n <- n + 1
}
dst <- filter(d, group == "DST states")
w0 <- win(dst, "days_from_spring") |> mutate(st_patricks = as.integer(month(date) == 3 & day(date) %in% 17:18))
rb <- read_csv("results/robustness.csv", show_col_types = FALSE)
checks <- list(est(w0), est(filter(w0, year != 2020)), est(w0, extra = "st_patricks"), est(filter(w0, st_patricks == 0)),
               est(win(dst, "days_from_spring", 21)), est(filter(w0, dow < 5)))
for (i in seq_along(checks)) {
  stopifnot(abs(checks[[i]]["coef"] - rb$coef[i]) < 1e-6, abs(checks[[i]]["se"] - rb$se[i]) < 1e-6)
  n <- n + 1
}
pl <- read_csv("results/placebo.csv", show_col_types = FALSE)
main_rr <- exp(checks[[1]]["coef"])
stopifnot(max(pl$rate_ratio) < main_rr)
cat(sprintf("OK: %d models refitted in R match statsmodels (coefficient and SE to 1e-6); spring rate ratio %.4f is above all %d placebo Sundays (max %.4f)\n",
            n, main_rr, nrow(pl), max(pl$rate_ratio)))
