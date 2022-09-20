from pathlib import Path

# The directory that this file is contained within
HERE = Path(__file__).resolve().parent

DATABASE_PATH = HERE / "ratings.sqlite3"

# compiler.properties file and metadata.
PROPERTIES_FILE = HERE / "compiler.properties"
PROPERTIES_JDK_VERSION = "18+37"
PROPERTIES_SHA_256 = "afe2fe79779178c70dc8e68a67cb0748fbd5a7b3adb47567c1c6d26d764a67ef"
PROPERTIES_COMMIT_SHA = "0f2113cee79b9645105b4753c7d7eacb83b872c2"
PROPERTIES_PERMALINK = f"https://github.com/openjdk/jdk/blob/{PROPERTIES_COMMIT_SHA}/src/jdk.compiler/share/classes/com/sun/tools/javac/resources/compiler.properties"
