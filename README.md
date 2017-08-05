## Introduction

This is a work in progress project which I'm calling Athena.

WARNING: in case the previous statement wasn't clear enough, to state explicitly: there are code quality problems all over the place -- especially in the frontend, but everywhere else too -- this is a rough, WIP prototype!

Athena is a web application where people can get notifications about local- and state-level legislation they care about. The idea is that there are a lot of ways you find out about federal legislation, but it's easier to miss local stuff, where individual actions actually can have a bigger impact.

Users can search for legislation, save their searches, and choose to be notified daily or weekly about new documents matching their saved searches.

## Current state

Right now there are custom, hand-coded crawlers for a couple of city councils and a single state legislature. These crawlers are incomplete, and are only intended for data collection and prototyping. When the app is running, the UI works (mostly), and users can search, create saved searches, and receive notifications, for the cities/states we have.

Crawlers and the indexer are currently run with cron, primarily for data collection.

In the next stage, I am working on automated processing (using the data being collected now as training data), so in order to be able to scale to more cities and states.

## Contributing

If you're interested in this project, I'd love to have help, especially from a frontend developer and/or designer! Right now the frontend is some awful (terrible! really it's quite bad! worse than you are imagining!) hacked-together html files, with inline CSS and scripts and all kinds of bad stuff! It needs to be thrown away and completely redone.

## License

[GPLv3](COPYING)

