# frozen_string_literal: true

source "https://rubygems.org"

gem "jekyll-theme-chirpy", "~> 7.6"

gem "html-proofer", "~> 5.0", group: :test

# Ruby 3.0+ dropped webrick from default gems; needed for `jekyll serve`.
gem "webrick", "~> 1.9"

platforms :windows, :jruby do
  gem "tzinfo", ">= 1", "< 3"
  gem "tzinfo-data"
end

gem "wdm", "~> 0.2.0", :platforms => [:windows]
