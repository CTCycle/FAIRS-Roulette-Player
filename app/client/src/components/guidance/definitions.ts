import type { TipDefinition, TourDefinition } from './types';

export const TRAINING_TOUR: TourDefinition = {
    id: 'training-introduction',
    version: 1,
    title: 'Getting started with Training',
    route: '/training',
    steps: [
        {
            id: 'training-data',
            target: '[data-guidance-target="training-data"]',
            title: 'Start with data',
            body: 'Upload a CSV/XLSX file or use the generator to create a roulette dataset.',
        },
        {
            id: 'training-configuration',
            target: '[data-guidance-target="training-configuration"]',
            title: 'Configure a run',
            body: 'Choose a dataset, then open the training wizard. The defaults are a safe starting point.',
        },
        {
            id: 'training-monitor',
            target: '[data-guidance-target="training-monitor"]',
            title: 'Watch the run',
            body: 'Follow status, reward, capital, and charts here. Completed runs create reusable checkpoints.',
        },
    ],
};

export const INFERENCE_TOUR: TourDefinition = {
    id: 'inference-loop',
    version: 1,
    title: 'Run an inference session',
    route: '/inference',
    steps: [
        {
            id: 'inference-setup',
            target: '[data-guidance-target="inference-setup"]',
            title: 'Set up a session',
            body: 'Choose a checkpoint and compatible dataset, then set the starting capital and bet amount.',
        },
        {
            id: 'inference-play',
            target: '[data-guidance-target="inference-play"]',
            title: 'Get a prediction',
            body: 'Play starts the session and fetches the first prediction. It does not submit a wheel result for you.',
        },
        {
            id: 'inference-observation',
            target: '[data-guidance-target="inference-observation"]',
            title: 'Record the round',
            body: 'Enter the observed wheel value, confirm it, then request the next prediction.',
        },
    ],
};

export const TIPS: TipDefinition[] = [
    {
        id: 'tip-generator',
        title: 'Start with the generator',
        body: 'Use the synthetic generator when you want a quick baseline without preparing a file first.',
    },
    {
        id: 'tip-fixed-baseline',
        title: 'Keep a fixed-bet baseline',
        body: 'Run a fixed-bet configuration before enabling dynamic betting so you can compare strategy changes clearly.',
    },
    {
        id: 'tip-checkpoints',
        title: 'Reuse checkpoints',
        body: 'Open checkpoint metadata to inspect a run, evaluate it from a compatible dataset, or resume training later.',
    },
    {
        id: 'tip-inference-rounds',
        title: 'Inference moves in rounds',
        body: 'After each prediction, enter the observed value and confirm it before asking for the next prediction.',
    },
];
