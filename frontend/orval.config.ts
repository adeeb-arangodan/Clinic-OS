import { defineConfig } from 'orval'

// Regenerate with `npm run generate:api` whenever backend/schema.yml changes
// (CLAUDE.md rule 10). Generated output is committed so the frontend builds
// without a running backend.
export default defineConfig({
  sehaerp: {
    input: '../backend/schema.yml',
    output: {
      target: 'src/api/generated/api.ts',
      schemas: 'src/api/generated/model',
      client: 'react-query',
      httpClient: 'fetch',
      clean: true,
      override: {
        mutator: {
          path: 'src/api/http.ts',
          name: 'customFetch',
        },
        fetch: {
          // customFetch already returns the parsed body (or throws ApiError)
          includeHttpResponseReturnType: false,
        },
      },
    },
  },
})
