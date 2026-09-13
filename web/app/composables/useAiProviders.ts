import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { queryKeys } from '~/services/api/keys'
import { aiService } from '~/services/api/ai'
import type {
  AiProvider,
  AiProviderCatalog,
  AiProviderCreateInput,
  AiProviderUpdateInput,
} from '~/types/ai'

export function useAiProviders() {
  return useQuery<AiProvider[]>({
    queryKey: queryKeys.aiProviders,
    queryFn: () => aiService.list(),
    staleTime: 20_000,
  })
}

export function useAiProviderCatalog() {
  return useQuery<AiProviderCatalog>({
    queryKey: queryKeys.aiProviderCatalog,
    queryFn: () => aiService.supported(),
    staleTime: 5 * 60_000,
  })
}

function invalidateProviders(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: queryKeys.aiProviders })
  void queryClient.invalidateQueries({ queryKey: queryKeys.agentStatus })
}

export function useCreateAiProvider() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: AiProviderCreateInput) => aiService.create(input),
    onSuccess: () => invalidateProviders(queryClient),
  })
}

export function useUpdateAiProvider() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: AiProviderUpdateInput }) =>
      aiService.update(id, input),
    onSuccess: () => invalidateProviders(queryClient),
  })
}

export function useDeleteAiProvider() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => aiService.remove(id),
    onSuccess: () => invalidateProviders(queryClient),
  })
}

export function useTestAiProvider() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => aiService.test(id),
    onSuccess: () => invalidateProviders(queryClient),
  })
}

export function useActivateAiProvider() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => aiService.activate(id),
    onSuccess: () => invalidateProviders(queryClient),
  })
}
