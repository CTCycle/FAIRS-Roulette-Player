import { describe, expect, it } from 'vitest'
import { parseApiErrorDetail, parseDatasetId } from '../../src/utils/apiParsers'

describe('API response parsers', () => {
    it.each([
        [1, 1],
        [0, null],
        [-1, null],
        [1.5, null],
        ['1', null],
    ])('parses dataset id %s as %s', (value, expected) => {
        expect(parseDatasetId(value)).toBe(expected)
    })

    it('formats FastAPI field errors with their locations', () => {
        expect(parseApiErrorDetail({
            detail: [{ loc: ['body', 'episodes'], msg: 'Input should be greater than 0' }],
        }, 'Request failed.')).toBe('body.episodes: Input should be greater than 0')
    })

    it('uses the fallback when a payload has no readable detail', () => {
        expect(parseApiErrorDetail({ detail: [] }, 'Request failed.')).toBe('Request failed.')
    })
})
