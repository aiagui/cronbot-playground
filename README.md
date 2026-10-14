# cronbot-playground
Sandbox repository for Cronbot autonomous software engineering

## SHA-256 manifests

Generate a stable JSON manifest for all regular files below a directory:

```sh
python -m cronbot_toolkit.checksums path/to/directory
```

Entries contain the relative POSIX path, byte size, and SHA-256 digest. Symbolic
links are rejected so content outside the requested directory is never followed.
