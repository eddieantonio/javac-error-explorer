# javac error message explorer

This is a web application for viewing error messages from the JDK Java
compiler (`javac`).

# Compiler.properties

I have copied [`compiler.properties`][properties-jdk] from the [JDK
source code][jdk-github]. This is the source of all error messages!

[jdk-github]: https://github.com/openjdk/jdk/tree/jdk-18%2B37
[properties-jdk]: https://github.com/openjdk/jdk/blob/0f2113cee79b9645105b4753c7d7eacb83b872c2/src/jdk.compiler/share/classes/com/sun/tools/javac/resources/compiler.properties

See [`constants.py`](./constants.py) for metadata about this file.

# Copying

Everything except `compiler.properties` is © 2022 Eddie Antonio Santos,
and distributed under the terms of GPLv3.0 license.

`compilers.properties` is copyright (c) 1999, 2022, Oracle and/or its affiliates.
