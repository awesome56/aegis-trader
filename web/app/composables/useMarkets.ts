import { useQuery } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { queryKeys } from '~/services/api/keys'
import { marketsService } from '~/services/api/markets'
import type { AssetDetail, CandleSeries, CandleTimeframe, MarketOverview, Quote } from '~/types/market'

export function useMarkets() {
  return useQuery<MarketOverview>({
    queryKey: queryKeys.markets,
    queryFn: () => marketsService.overview(),
    staleTime: 10_000,
  })
}

export function useMarketAsset(symbol: MaybeRefOrGetter<string>) {
  return useQuery<AssetDetail>({
    queryKey: computed(() => queryKeys.asset(toValue(symbol))),
    queryFn: () => marketsService.asset(toValue(symbol)),
    enabled: computed(() => Boolean(toValue(symbol))),
  })
}

export function useMarketQuote(symbol: MaybeRefOrGetter<string>) {
  return useQuery<Quote>({
    queryKey: computed(() => [...queryKeys.asset(toValue(symbol)), 'quote'] as const),
    queryFn: () => marketsService.quote(toValue(symbol)),
    enabled: computed(() => Boolean(toValue(symbol))),
    staleTime: 5_000,
  })
}

export function useMarketCandles(
  symbol: MaybeRefOrGetter<string>,
  timeframe: MaybeRefOrGetter<CandleTimeframe>,
) {
  return useQuery<CandleSeries>({
    queryKey: computed(() => queryKeys.candles(toValue(symbol), toValue(timeframe))),
    queryFn: () => marketsService.candles(toValue(symbol), toValue(timeframe)),
    enabled: computed(() => Boolean(toValue(symbol))),
    staleTime: 15_000,
  })
}
