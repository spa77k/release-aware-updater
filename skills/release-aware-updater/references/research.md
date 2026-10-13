# Evidence and artifact checks

## Minecraft plugin/JAR updates

1. Establish the actual upstream project and distribution channel from repository
   history or the publisher's site. Similar names and unofficial mirrors are not
   sufficient. Some plugins publish on GitHub; others use Modrinth, Hangar,
   SpigotMC, or a vendor portal. Use an available official API or read the official
   page. No universal release scraper is bundled.
2. Read candidate and intervening release notes. Match Minecraft version, server
   implementation (Paper/Spigot/Folia/Velocity/etc.), Java version, and required
   companion plugins. Folia support and proxy/server compatibility are separate
   facts; never infer them from a generic “Minecraft plugin” label.
3. Select the actual binary artifact, not a source archive, installer, dev build,
   or similarly named asset. Record the immutable release/version identifier,
   asset name and official download URL. An API listing alone is not release-note
   review. GitHub `latest` is not a compatibility resolver.
4. Check publisher-provided hashes/signatures when available. GitHub asset
   metadata may expose a digest; Modrinth file objects document hashes. Preserve
   the algorithm rather than relabeling SHA-1 or SHA-512 as SHA-256. If only another
   trusted algorithm is supplied, verify it first and then compute SHA-256 from
   the same bytes for the pin. Do not invent a digest when metadata is missing.
5. If authorized to download the binary, use the official HTTPS source, verify
   redirects still match the publisher's distribution, avoid executing it, and
   hash it locally. The helper can compare the bytes to a known SHA-256:

   ```sh
   python3 <skill-dir>/scripts/update.py sha256 <downloaded.jar> --expected <sha256>
   ```

A locally computed checksum fixes the bytes for future reproducibility; by
itself it does not authenticate the publisher. Record the official source and
the exact verification performed, including absent signatures/checksums. Respect
the host's download/install permissions. Never place a downloaded JAR directly
into a live server directory as an implicit test.

## Docker images

- Read the upstream application's release notes and the image-maintainer's notes.
  An unchanged application version can still receive a changed base image. Match
  the variant (for example JRE/JDK, Alpine/Debian), configuration contract, and
  required platform; do not silently switch publishers or registries.
- Tags are mutable. Record an immutable `repository:tag@sha256:...` reference (a
  digest-only repository reference is also valid). Inspect the registry manifest
  with a suitable read-only registry tool, such as an available
  `docker buildx imagetools inspect <reference>`. Do not pull/run automatically.
- Distinguish a multi-platform image index/manifest list digest from an individual
  platform manifest digest. Check the requested `os/architecture[/variant]` is
  included. Preserve the project's existing choice when appropriate. A local
  Docker image ID/config digest is not the registry manifest digest.
- Pin the verified digest returned by the registry; do not hash release-note
  text, a displayed JSON document, or a tag string to create a substitute.
- Read database/world format changes and downgrade limitations. Persistent
  volumes remain changed even if an earlier image starts. Preserve a restorable
  snapshot and document the compatible previous image.

## Source failure and uncertainty

Report a hold when official notes or compatibility evidence cannot be accessed.
A private registry, anti-bot page, rate limit, missing checksum, or unrecognized
distribution format is a limitation to disclose. Do not bypass access controls,
send credentials to mirrors, use a “latest” guess, or relabel unknown as pass.
Missing signatures alone do not make a project unusable: explain the actual
trust level and let the user's existing policy govern whether it is acceptable.

## Official references

These describe formats and workflows, not a current version recommendation.
Re-check the relevant upstream release when using the skill.

- [Paper updating guidance](https://docs.papermc.io/paper/updating/)
- [GitHub release API](https://docs.github.com/en/rest/releases/releases)
- [Modrinth version and file metadata](https://docs.modrinth.com/api/operations/getversion/)
- [Docker digest pulls](https://docs.docker.com/reference/cli/docker/image/pull/)
- [Docker image pinning guidance](https://docs.docker.com/build/building/best-practices/)
- [Docker manifest inspection](https://docs.docker.com/reference/cli/docker/buildx/imagetools/inspect/)
