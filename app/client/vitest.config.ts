// Copyright © 2023 Thomas Virdis
// Licensed under the MIT License.

import { defineConfig } from 'vitest/config'

export default defineConfig({
    test: {
        environment: 'node',
        include: ['tests/unit/**/*.test.ts'],
        clearMocks: true,
        restoreMocks: true,
    },
})
