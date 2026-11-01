import json
from pathlib import Path


def ensure_dockerfile(project_path):
    """
    Keep an existing Dockerfile unchanged.
    Generate a production Dockerfile for supported Vite projects.
    """
    project = Path(project_path).expanduser().resolve()
    dockerfile = project / "Dockerfile"

    if dockerfile.is_file():
        print(f"Using existing Dockerfile: {dockerfile}")
        return dockerfile

    package_file = project / "package.json"

    if not package_file.is_file():
        raise ValueError(
            f"package.json not found in {project}"
        )

    with package_file.open("r", encoding="utf-8") as file:
        package = json.load(file)

    scripts = package.get("scripts", {})
    dependencies = {
        **package.get("dependencies", {}),
        **package.get("devDependencies", {}),
    }

    if "build" not in scripts:
        raise ValueError(
            "The project must have a build script in package.json."
        )

    if "vite" not in dependencies:
        raise ValueError(
            "Automatic Dockerfile generation currently supports "
            "Vite projects. This project does not declare Vite."
        )

    if not (project / "index.html").is_file():
        raise ValueError(
            "Vite project index.html was not found."
        )

    if (project / "package-lock.json").is_file():
        install_command = "RUN npm ci"
    else:
        install_command = "RUN npm install"

    content = f"""# Generated automatically by deploy-tool
# Stage 1: Build the Vite/React application
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
{install_command}

COPY . .
RUN npm run build

# Stage 2: Serve the production website
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
"""

    dockerfile.write_text(content, encoding="utf-8")
    print(f"Generated Dockerfile automatically: {dockerfile}")

    return dockerfile
