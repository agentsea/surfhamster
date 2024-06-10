# SurfHamster

The AI agent that can navigate GUIs and do tasks in them.

## Install
```sh
pip install surfkit
```

## Usage

Create an agent
```sh
surfkit create agent -f ./agent.yaml --runtime { process | docker | kube } --name foo
```

List running agents
```sh
surfkit list agents
```

Use the agent to solve a task
```sh
surfkit solve --agent foo --description "Search for french ducks" --device-type desktop
```

Get the agent logs
```sh
surfkit logs --name foo
```

Delete the agent
```sh
surfkit delete agent --name foo
```

