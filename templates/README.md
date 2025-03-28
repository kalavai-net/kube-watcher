# Community integrations for Kalavai

> **Under construction**. This section is likely to change considerably. Feel free to tinker with templates, but beware that breaking changes may occur.

Template jobs built by Kalavai and the community make deploying distributed workflows easy for end users.

Templates are like recipes, where **developers describe what worker nodes should run**, and **users customise the behaviour via pre-defined parameters**. **Kalavai handles the heavy lifting**: workload distribution, communication between nodes and monitoring the state of the deployment to restart the job if required.


## List of available templates

- [vLLM](./vllm): deploy your favourite LLMs in distributed machines.
- [llama.cpp](./llamacpp): deploy llama.cpp models (CPU and GPU) in distributed machines.
- [Aphrodite](./aphrodite): deploy your favourite LLMs in distributed machines.
- [Petals](./petals): bit-torrent style deployment of LLMs
- [litellm](./litellm/): Unified LLM API.
- [playground](./playground/): Unified UI playground.


## How to contribute

Do you want to **develop your own template** and share it with the community? We are working on a path to make it easier for developers to do so. Hang on tight! [Register your interest](http://eepurl.com/iC89hk) and we'll ping you when we are ready!

For now, if you feel adventurous, here's how to get started:


1. Clone the repository

```bash
git clone https://github.com/kalavai-net/kube-watcher/
```

2. Duplicate the `templates/dummy` folder and rename it to your new template name
```bash
cd kube-watcher
mkdir -p templates/new_template
cp -r templates/dummy templates/new_template
```

3. Your template is expected to contain at least 3 files:
* `template.yaml`: this is the distributed job template that tells Kalavai how to run a job
* `values.yaml`: a list of default values, including descriptions for each. Variable names will populate the template when users run your template.
* `README.md`: any details you may want users to know about your template job.

4. Develop your template. We use [Volcano jobs](https://volcano.sh/en/docs/vcjob/).

5. Templatise your job with variables. Whenever you want a placeholder value, insert `$name_of_the_variable` in your `template.yaml`, and list your new variable under `values.yaml`.

6. Test your template with the `kalavai` cli when ready! TODO

7. (Optional) If you want to contribute your template to the community so others can use it, push a PR to the kalavai-client repository containing your `templates/new_template` folder

