import argparse
import droveclient
import droveutils
import json
import plugins

from operator import itemgetter
from types import SimpleNamespace

class Applications(plugins.DrovePlugin):
    def __init__(self) -> None:
        pass

    def populate_options(self, drove_client: droveclient.DroveClient, subparser: argparse.ArgumentParser):
        parser = subparser.add_parser("apps", help="Drove application related commands")

        commands = parser.add_subparsers(help="Available commands for application management")

        sub_parser = commands.add_parser("list", help="List all applications")
        sub_parser.add_argument("--sort", "-s", help="Sort output by column", type=int, choices=range(0, 9), default = 0)
        sub_parser.add_argument("--reverse", "-r", help="Sort in reverse order", action="store_true")
        sub_parser.set_defaults(func=self.list_apps)

        sub_parser = commands.add_parser("summary", help="Show a summary for an application")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.set_defaults(func=self.show_summary)

        sub_parser = commands.add_parser("spec", help="Print the raw json spec for an application")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.set_defaults(func=self.show_spec)

        sub_parser = commands.add_parser("create", help="Create application on cluster")
        sub_parser.add_argument("spec_file", metavar="spec-file", help="JSON spec file for the application")
        sub_parser.set_defaults(func=self.create_app)
        
        sub_parser = commands.add_parser("destroy", help="Destroy an app with zero instances")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.set_defaults(func=self.destroy_app)

        sub_parser = commands.add_parser("deploy", help="Deploy new app instances.")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("instances", metavar="instances", type=int, help="Number of new instances to be created")
        sub_parser.add_argument("--parallelism", "-p", help="Number of parallel threads to be used to execute operation", type=int, default = 1)
        sub_parser.add_argument("--timeout", "-t", help="Timeout for the operation on the cluster", type=str, default = "5m")
        sub_parser.set_defaults(func=self.deploy_app)


        sub_parser = commands.add_parser("scale", help="Scale app to required instances. Will increase or decrease instances on the cluster to match this number")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("instances", metavar="instances", type=int, help="Number of instances. Setting this to 0 will suspend the app")
        sub_parser.add_argument("--parallelism", "-p", help="Number of parallel threads to be used to execute operation", type=int, default = 1)
        sub_parser.add_argument("--timeout", "-t", help="Timeout for the operation on the cluster", type=str, default = "5m")
        sub_parser.set_defaults(func=self.scale_app)

        sub_parser = commands.add_parser("suspend", help="Suspend the app")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("--parallelism", "-p", help="Number of parallel threads to be used to execute operation", type=int, default = 1)
        sub_parser.add_argument("--timeout", "-t", help="Timeout for the operation on the cluster", type=str, default = "5m")
        sub_parser.set_defaults(func=self.suspend_app)

        sub_parser = commands.add_parser("restart", help="Restart am existing app instances.")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.add_argument("--parallelism", "-p", help="Number of parallel threads to be used to execute operation", type=int, default = 1)
        sub_parser.add_argument("--timeout", "-t", help="Timeout for the operation on the cluster", type=str, default = "5m")
        sub_parser.set_defaults(func=self.restart_app)

        sub_parser = commands.add_parser("cancelop", help="Cancel current operation")
        sub_parser.add_argument("app_id", metavar="app-id", help="Application ID")
        sub_parser.set_defaults(func=self.cancel_app_operation)

        # sub_parser = commands.add_parser("create", help="Create application")
        # sub_parser.add_argument("definition", help="JSON application definition")
        
        super().populate_options(drove_client, parser)


    def list_apps(self, options: SimpleNamespace):
        data = self.drove_client.get('/apis/v1/applications')
        app_rows = []
        for app_id, app_data in data.items():
            row = []
            row.append(app_id)
            row.append(app_data["name"])
            row.append(app_data["state"])
            row.append(app_data["totalCPUs"])
            row.append(app_data["totalMemory"])
            row.append(app_data["requiredInstances"])
            row.append(app_data["healthyInstances"])
            row.append(droveutils.to_date(app_data["created"]))
            row.append(droveutils.to_date(app_data["updated"]))

            app_rows.append(row)

        app_rows = sorted(app_rows, key=itemgetter(options.sort), reverse=options.reverse)

        headers = ["Id", "Name", "State", "Total CPU", "Total Memory(MB)", "Required Instances", "Healthy Instances", "Created", "Updated"]
        droveutils.print_table(headers, app_rows)

    def show_summary(self, options: SimpleNamespace):
        data = self.drove_client.get("/apis/v1/applications/{app_id}".format(app_id = options.app_id))
        droveutils.print_dict(data)

    def show_spec(self, options: SimpleNamespace):
        data = self.drove_client.get("/apis/v1/applications/{app_id}/spec".format(app_id = options.app_id))
        droveutils.print_json(data)

    def create_app(self, options: SimpleNamespace):
        try:
            with open(options.spec_file, 'r') as fp:
                spec = json.load(fp)
            operation = {
                "type": "CREATE",
                "spec": spec,
                "opSpec": {
                   "timeout": "5m",
                    "parallelism": 1,
                    "failureStrategy": "STOP"
                }
            }
            data = self.drove_client.post("/apis/v1/applications/operations", operation)
            print("Application created with app id: {appid}".format(appid=data["appId"]))
        except droveclient.DroveException as e:
            print("Error creating app: {error}".format(error = str(e)))
        except Exception as e:
            print("Error creating application. Error: " + str(e))

    def destroy_app(self, options: SimpleNamespace):
        try:
            operation = {
                "type": "DESTROY",
                "appId": options.app_id,
                "opSpec": {
                   "timeout": "5m",
                    "parallelism": 1,
                    "failureStrategy": "STOP"
                }
            }
            data = self.drove_client.post("/apis/v1/applications/operations", operation)
            print("Application destroyed")
        except droveclient.DroveException as e:
            print("Error destroying app: {error}".format(error = str(e)))

    def scale_app(self, options: SimpleNamespace):
        try:
            operation = {
                "type": "SCALE",
                "appId": options.app_id,
                "requiredInstances": options.instances,
                "opSpec": {
                   "timeout": options.timeout,
                    "parallelism": options.parallelism,
                    "failureStrategy": "STOP"
                }
            }
            data = self.drove_client.post("/apis/v1/applications/operations", operation)
            print("Application scaling command accepted. Please use appinstances comand or the UI to check status of deployment")
        except droveclient.DroveException as e:
            print("Error scaling app: {error}".format(error = str(e)))

    def suspend_app(self, options: SimpleNamespace):
        try:
            operation = {
                "type": "SUSPEND",
                "appId": options.app_id,
                "opSpec": {
                   "timeout": options.timeout,
                    "parallelism": options.parallelism,
                    "failureStrategy": "STOP"
                }
            }
            data = self.drove_client.post("/apis/v1/applications/operations", operation)
            print("Application suspend command accepted.")
        except droveclient.DroveException as e:
            print("Error suspending app: {error}".format(error = str(e)))

    def deploy_app(self, options: SimpleNamespace):
        try:
            operation = {
                "type": "START_INSTANCES",
                "appId": options.app_id,
                "instances": options.instances,
                "opSpec": {
                   "timeout": options.timeout,
                    "parallelism": options.parallelism,
                    "failureStrategy": "STOP"
                }
            }
            data = self.drove_client.post("/apis/v1/applications/operations", operation)
            print("Application deployment command accepted. Please use appinstances comand or the UI to check status of deployment")
        except droveclient.DroveException as e:
            print("Error deploying instances for app: {error}".format(error = str(e)))

    def restart_app(self, options: SimpleNamespace):
        try:
            operation = {
                "type": "REPLACE_INSTANCES",
                "appId": options.app_id,
                "opSpec": {
                   "timeout": options.timeout,
                    "parallelism": options.parallelism,
                    "failureStrategy": "STOP"
                }
            }
            data = self.drove_client.post("/apis/v1/applications/operations", operation)
            print("Application restart command accepted.")
        except droveclient.DroveException as e:
            print("Error suspending app: {error}".format(error = str(e)))

    def cancel_app_operation(self, options: SimpleNamespace):
        try:
            self.drove_client.post("/apis/v1/operations/{appId}/cancel".format(appId=options.app_id), None, False)
            print("Operation cancellation request registered.")
        except droveclient.DroveException as e:
            print("Error suspending app: {error}".format(error = str(e)))
